"""Round flange family — cylinder with optional bolt holes and fillet."""

import math

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class RoundFlangeFamily(BaseFamily):
    """Parametric round flange: outer cylinder + center bore + bolt pattern."""

    name = "round_flange"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a round flange at given difficulty."""
        outer_r = rng.uniform(20, 100)
        inner_r = rng.uniform(3, outer_r * 0.4)
        height = rng.uniform(max(5, outer_r * 0.12), 30)

        params = {
            "outer_radius": round(outer_r, 1),
            "inner_radius": round(inner_r, 1),
            "height": round(height, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Bolt circle
            bolt_r_min = inner_r + 3
            bolt_r_max = outer_r - 3
            if bolt_r_max <= bolt_r_min:
                bolt_r_max = bolt_r_min + 1
            bolt_r = rng.uniform(bolt_r_min, bolt_r_max)
            n_bolts = rng.choice([4, 6, 8])
            pitch = 2 * math.pi * bolt_r / n_bolts
            max_bolt_d = min(pitch / 2, (outer_r - bolt_r - 1) * 2, (bolt_r - inner_r - 1) * 2)
            bolt_d = rng.uniform(2, max(2.5, max_bolt_d * 0.6))
            params["bolt_circle_radius"] = round(bolt_r, 1)
            params["bolt_count"] = int(n_bolts)
            params["bolt_hole_diameter"] = round(bolt_d, 1)

        if difficulty in ("medium", "hard"):
            # Chamfer on bottom face edge (more reliable than fillet on cylinder)
            ch = rng.uniform(0.3, min(2.0, height / 4))
            params["chamfer_length"] = round(ch, 1)

        if difficulty in ("medium", "hard"):
            rfr = round(outer_r * rng.uniform(0.55, 0.72), 1)
            rfh = round(rng.uniform(1.5, max(1.6, height * 0.15)), 1)
            params["raised_face_radius"] = rfr
            params["raised_face_height"] = rfh

        if difficulty == "hard":
            rfr = params["raised_face_radius"]
            rfh = params["raised_face_height"]
            nr = round(rfr * rng.uniform(0.55, 0.78), 1)
            nh = round(rng.uniform(height * 0.5, height * 1.5), 1)
            params["neck_radius"] = nr
            params["neck_height"] = nh

        return params

    def validate_params(self, params: dict) -> bool:
        """Validate round flange constraints."""
        ir = params["inner_radius"]
        otr = params["outer_radius"]
        h = params["height"]

        if ir >= otr:
            return False
        if h < 2 or h < otr * 0.08:
            return False

        bcr = params.get("bolt_circle_radius")
        if bcr is not None:
            if bcr <= ir + 3 or bcr >= otr - 3:
                return False
            bd = params.get("bolt_hole_diameter", 0)
            n = params.get("bolt_count", 4)
            pitch = 2 * math.pi * bcr / n
            if bd >= pitch / 2:
                return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= h / 4:
            return False

        rfr = params.get("raised_face_radius")
        if rfr is not None and rfr >= otr:
            return False

        nr = params.get("neck_radius")
        rfr2 = params.get("raised_face_radius")
        if nr is not None and rfr2 is not None and nr >= rfr2:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        """Build program for round flange."""
        difficulty = params.get("difficulty", "easy")
        ops = []
        tags = {
            "has_hole": False,
            "has_chamfer": False,
            "has_bolt_pattern": False,
            "has_hub": False,
            "pattern_like": False,
        }

        # Outer cylinder (flange disc)
        ops.append(Op("cylinder", {"height": params["height"],
                                    "radius": params["outer_radius"]}))

        # Chamfer bottom outer edge first — before holes pierce <Z face
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Bolt pattern on flange face (medium/hard) — before raised face so >Z = flange top
        bcr = params.get("bolt_circle_radius")
        if bcr is not None:
            tags["has_bolt_pattern"] = True
            tags["pattern_like"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op("polarArray", {
                    "radius": bcr,
                    "startAngle": 0,
                    "angle": 360,
                    "count": params["bolt_count"],
                })
            )
            ops.append(Op("hole", {"diameter": params["bolt_hole_diameter"]}))

        # Raised face (medium+)
        rfr = params.get("raised_face_radius")
        rfh = params.get("raised_face_height")
        if rfr and rfh:
            tags["has_hub"] = True
            ops.append(Op("union", {"ops": [
                {"name": "transformed", "args": {"offset": [0, 0, round(params["height"] / 2 + rfh / 2, 3)], "rotate": [0, 0, 0]}},
                {"name": "cylinder", "args": {"height": rfh, "radius": rfr}},
            ]}))

        # Neck (hard)
        nr = params.get("neck_radius")
        nh = params.get("neck_height")
        if nr and nh and rfh:
            neck_z = params["height"] / 2 + rfh
            ops.append(Op("union", {"ops": [
                {"name": "transformed", "args": {"offset": [0, 0, round(neck_z + nh / 2, 3)], "rotate": [0, 0, 0]}},
                {"name": "cylinder", "args": {"height": nh, "radius": nr}},
            ]}))

        # Center bore — last, through full assembly (flange + raised face + neck)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": params["inner_radius"] * 2}))
        tags["has_hole"] = True

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
