"""Fan shroud — square plate with central circular fan opening.

Common in cooling systems, HVAC, electronics enclosures.

Easy:   rectangular plate + central circular cutout.
Medium: + 4 corner mounting holes.
Hard:   + raised cylindrical collar around fan opening.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class FanShroudFamily(BaseFamily):
    name = "fan_shroud"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        fan_r = round(rng.uniform(30, 80), 1)
        margin = round(rng.uniform(15, 35), 1)
        side = round(2 * fan_r + 2 * margin, 1)
        thick = round(rng.uniform(4, 12), 1)

        params = {
            "fan_radius": fan_r,
            "plate_side": side,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["hole_diameter"] = round(rng.uniform(3, min(margin * 0.5, 8)), 1)

        if difficulty == "hard":
            params["collar_height"] = round(rng.uniform(6, 18), 1)
            params["collar_width"] = round(rng.uniform(3, 8), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        fan_r = params["fan_radius"]
        side = params["plate_side"]
        thick = params["thickness"]

        margin = side / 2 - fan_r
        if margin < 10:
            return False
        if fan_r >= side / 2 - 8:
            return False
        if thick < 3:
            return False
        if side < 80:
            return False

        hd = params.get("hole_diameter", 0)
        if hd and hd >= margin * 0.6:
            return False

        cw = params.get("collar_width", 0)
        if cw and cw < 2:
            return False
        ch = params.get("collar_height", 0)
        if ch and ch < 3:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        fan_r = params["fan_radius"]
        side = params["plate_side"]
        thick = params["thickness"]

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # Square plate
        ops.append(
            Op(
                "box",
                {
                    "length": round(side, 4),
                    "width": round(side, 4),
                    "height": round(thick, 4),
                },
            )
        )

        # Central fan opening
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": round(fan_r, 4)}))
        ops.append(Op("cutThruAll", {}))

        # Corner mounting holes (medium+)
        hd = params.get("hole_diameter")
        if hd:
            margin = side / 2 - fan_r
            offset = round(side / 2 - margin / 2, 4)
            pts = [
                (offset, offset),
                (-offset, offset),
                (offset, -offset),
                (-offset, -offset),
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": pts}))
            ops.append(Op("hole", {"diameter": round(hd, 4)}))

        # Raised collar ring around fan opening (hard)
        # Collar sits on top face, along Z (XY_ONLY so Z is always the plate normal)
        ch = params.get("collar_height")
        cw = params.get("collar_width")
        if ch and cw:
            collar_outer_r = round(fan_r + cw, 4)
            collar_cz = round(thick / 2 + ch / 2, 4)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, collar_cz],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ch, 4),
                                    "radius": collar_outer_r,
                                },
                            },
                        ]
                    },
                )
            )
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, collar_cz],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ch + 1, 4),
                                    "radius": round(fan_r, 4),
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
