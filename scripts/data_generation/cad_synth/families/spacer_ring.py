"""Spacer ring — thin-wall hollow cylinder with symmetric axial holes.

Typical use: shaft spacer, bearing shim, sleeve bushing.
Easy:   hollow cylinder (bore + outer)
Medium: + N symmetric through-holes parallel to axis
Hard:   + internal snap groove on bore face
"""

import math

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class SpacerRingFamily(BaseFamily):
    name = "spacer_ring"
    standard = "DIN 988"

    def sample_params(self, difficulty: str, rng) -> dict:
        od = rng.uniform(15, 120)
        wall_t = rng.uniform(2, min(15, od * 0.3))
        height = rng.uniform(3, min(40, od * 0.8))

        params = {
            "outer_diameter": round(od, 1),
            "wall_thickness": round(wall_t, 1),
            "height": round(height, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            n_holes = int(rng.choice([4, 6]))
            id_r = od / 2 - wall_t
            hole_pcd = round((id_r + od / 2) / 2, 1)
            max_hole_d = min(3.5, wall_t * 0.5, 2 * math.pi * hole_pcd / n_holes * 0.35)
            hole_d = round(rng.uniform(1.5, max(1.6, max_hole_d)), 1)
            params["n_holes"] = n_holes
            params["hole_pcd"] = hole_pcd
            params["hole_diameter"] = hole_d

        if difficulty == "hard":
            groove_w = round(rng.uniform(1.0, max(1.1, min(3.0, height * 0.25))), 1)
            groove_d = round(rng.uniform(0.5, max(0.6, min(2.0, wall_t * 0.3))), 1)
            params["groove_width"] = groove_w
            params["groove_depth"] = groove_d

        return params

    def validate_params(self, params: dict) -> bool:
        od = params["outer_diameter"]
        wt = params["wall_thickness"]
        h = params["height"]
        id_r = od / 2 - wt

        if wt < 1.5 or h < 2 or id_r < 3:
            return False

        hp = params.get("hole_pcd")
        hd = params.get("hole_diameter")
        if hp and hd:
            if hp - hd / 2 <= id_r or hp + hd / 2 >= od / 2:
                return False

        gw = params.get("groove_width")
        gd = params.get("groove_depth")
        if gw and gd:
            if gw >= h * 0.4 or gd >= wt * 0.4:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        od = params["outer_diameter"]
        wt = params["wall_thickness"]
        h = params["height"]
        id_r = od / 2 - wt

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Hollow cylinder along Z axis — bore + outer
        ops.append(Op("cylinder", {"height": h, "radius": round(od / 2, 3)}))
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(id_r * 2, 3)}))

        # Symmetric axial through-holes (medium+) — parallel to Z axis via polarArray
        hp = params.get("hole_pcd")
        hd = params.get("hole_diameter")
        n_h = params.get("n_holes")
        if hp and hd and n_h:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op(
                    "polarArray",
                    {
                        "radius": hp,
                        "startAngle": 0,
                        "angle": 360,
                        "count": n_h,
                    },
                )
            )
            ops.append(Op("hole", {"diameter": round(hd, 3)}))

        # Internal snap groove on bore surface (hard)
        # Cut a thin cylinder of radius (id_r + gd) centered axially at h/2.
        # Since the bore (radius=id_r) is already empty, this removes only the
        # annular ring id_r → id_r+gd at that axial position.
        gw = params.get("groove_width")
        gd = params.get("groove_depth")
        if gw and gd:
            tags["has_slot"] = True
            groove_base = round(h / 2 - gw / 2, 3)
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, groove_base],
                                    "rotate": [0.0, 0.0, 0.0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(gw, 3),
                                    "radius": round(id_r + gd, 3),
                                },
                            },
                        ]
                    },
                )
            )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
