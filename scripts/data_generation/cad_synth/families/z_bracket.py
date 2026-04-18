"""Z-bracket / multi-arm bracket — chained face-workplane perpendicular arms.

Structural type: box base + faces(>Y).workplane.box perpendicular arms.
Covers: z-brackets, wall-mount brackets, hook brackets, L/Z/T arms.

Easy:   base plate + one perpendicular arm (L-bracket variant)
Medium: + second arm at opposite end (Z-shape) + mounting holes
Hard:   + gusset rib + extra offset arm + chamfer
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program


class ZBracketFamily(BaseFamily):
    name = "z_bracket"

    def sample_params(self, difficulty: str, rng) -> dict:
        base_l = rng.uniform(40, 120)
        base_w = rng.uniform(20, 60)
        base_t = rng.uniform(4, max(4.1, min(12, base_w * 0.2)))
        arm_h = rng.uniform(20, max(20.1, base_l * 0.6))
        arm_t = rng.uniform(4, max(4.1, min(10, base_t * 1.5)))

        params = {
            "base_length": round(base_l, 1),
            "base_width": round(base_w, 1),
            "base_thickness": round(base_t, 1),
            "arm_height": round(arm_h, 1),
            "arm_thickness": round(arm_t, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Number of mounting holes on base
            n_holes = int(rng.choice([2, 4]))
            hole_d = round(rng.uniform(4, max(4.1, min(10, base_t * 1.2))), 1)
            params["n_base_holes"] = n_holes
            params["hole_diameter"] = hole_d
            # Second arm offset (Z shape)
            arm2_offset = round(rng.uniform(base_l * 0.3, base_l * 0.6), 1)
            params["arm2_offset"] = arm2_offset

        if difficulty == "hard":
            params["chamfer_length"] = round(rng.uniform(1, max(1.1, base_t * 0.2)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        bl = params["base_length"]
        bw = params["base_width"]
        bt = params["base_thickness"]
        ah = params["arm_height"]
        at = params["arm_thickness"]

        if bt >= bw * 0.4 or at >= bw * 0.4:
            return False
        if ah < 10 or bl < 20:
            return False

        hd = params.get("hole_diameter")
        if hd and hd >= bt * 1.8:
            return False

        a2o = params.get("arm2_offset")
        if a2o and a2o >= bl * 0.8:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bl = params["base_length"]
        bw = params["base_width"]
        bt = params["base_thickness"]
        ah = params["arm_height"]
        at = params["arm_thickness"]

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
        }

        # Base plate
        ops.append(Op("box", {"length": bl, "width": bw, "height": bt}))

        # Chamfer (hard) — BEFORE arms to avoid multi-arm top topology failure
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # First perpendicular arm at one end of base plate
        # Position: at x = +bl/2 edge, extends in +Z
        arm1_x = round(bl / 2 - at / 2, 3)
        arm1_z = round(bt / 2 + ah / 2 - 0.5, 3)
        ops.append(Op("union", {"ops": [
            {"name": "transformed", "args": {
                "offset": [arm1_x, 0, arm1_z],
                "rotate": [0, 0, 0],
            }},
            {"name": "box", "args": {
                "length": at,
                "width": bw,
                "height": ah,
                "centered": True,
            }},
        ]}))

        # Mounting holes on base plate (medium+)
        n_mh = params.get("n_base_holes")
        hd = params.get("hole_diameter")
        if n_mh and hd:
            tags["has_hole"] = True
            if n_mh == 2:
                spacing = round(bl * 0.5, 3)
                mh_pts = [(-spacing / 2, 0.0), (spacing / 2, 0.0)]
            else:
                sx = round(bl * 0.35, 3)
                sy = round(bw * 0.3, 3)
                mh_pts = [(-sx, -sy), (-sx, sy), (sx, -sy), (sx, sy)]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": mh_pts}))
            ops.append(Op("hole", {"diameter": hd}))

        # Second arm (Z shape — medium+)
        a2o = params.get("arm2_offset")
        if a2o is not None:
            arm2_x = round(-bl / 2 + at / 2 + a2o, 3)
            arm2_z = round(bt / 2 + ah / 2 - 0.5, 3)
            ops.append(Op("union", {"ops": [
                {"name": "transformed", "args": {
                    "offset": [arm2_x, 0, arm2_z],
                    "rotate": [0, 0, 0],
                }},
                {"name": "box", "args": {
                    "length": at,
                    "width": bw,
                    "height": ah,
                    "centered": True,
                }},
            ]}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
