"""Eyebolt (吊环螺栓) — forged lifting eye per DIN 580.

Composed of four primary solids, unioned:
  1. Threaded shank — cylinder Ø d1, length l, below the collar (z = -l .. 0)
  2. Collar/flange  — cylinder Ø d2, thickness e            (z = 0 .. e)
  3. Neck           — loft from circle Ø neck_base at z=e to Ø m at the eye
  4. Eye ring       — torus (major_R, minor_R) with axis Y at eye_center_z

Eye geometry: d3 = eye outer diameter, d4 = eye inner diameter,
  major_R = (d3 + d4)/4, minor_R = (d3 - d4)/4,
  eye_center_z = h - d3/2 (h is total bolt height).

Easy:   M8–M16 (common rigging sizes)
Medium: M12–M24
Hard:   M20–M36 (heavy lifting)

Reference: DIN 580:2010 — Lifting eye bolts — Tapping thread; Table 1
  (M8..M36 with d1, l, d2, d3, d4, h, e tolerances).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 580:2010 Table 1 — full M8..M36 series
# (d1 thread dia, l thread length, d2 collar OD, d3 eye OD, d4 eye ID,
#  h total height, e collar thickness, m neck top width).
_DIN580 = {
    "M8": {"d1": 8, "l": 13, "d2": 20, "d3": 36, "d4": 20, "h": 36, "e": 6, "m": 10},
    "M10": {"d1": 10, "l": 17, "d2": 25, "d3": 45, "d4": 25, "h": 45, "e": 8, "m": 12},
    "M12": {
        "d1": 12,
        "l": 20.5,
        "d2": 30,
        "d3": 54,
        "d4": 30,
        "h": 53,
        "e": 10,
        "m": 14,
    },
    "M16": {"d1": 16, "l": 27, "d2": 35, "d3": 63, "d4": 35, "h": 62, "e": 12, "m": 16},
    "M20": {"d1": 20, "l": 30, "d2": 40, "d3": 72, "d4": 40, "h": 71, "e": 14, "m": 19},
    "M24": {"d1": 24, "l": 36, "d2": 50, "d3": 90, "d4": 50, "h": 90, "e": 18, "m": 24},
    "M30": {
        "d1": 30,
        "l": 45,
        "d2": 60,
        "d3": 108,
        "d4": 60,
        "h": 107,
        "e": 22,
        "m": 28,
    },
    "M36": {
        "d1": 36,
        "l": 54,
        "d2": 70,
        "d3": 126,
        "d4": 70,
        "h": 124,
        "e": 26,
        "m": 32,
    },
}


class EyeboltFamily(BaseFamily):
    name = "eyebolt"
    standard = "DIN 580"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = ["M8", "M10", "M12", "M16"]
        elif difficulty == "medium":
            pool = ["M12", "M16", "M20", "M24"]
        else:
            pool = ["M20", "M24", "M30", "M36"]
        size = str(rng.choice(pool))
        d = _DIN580[size]
        params = {
            "size": size,
            "d1": float(d["d1"]),
            "l": float(d["l"]),
            "d2": float(d["d2"]),
            "d3": float(d["d3"]),
            "d4": float(d["d4"]),
            "h": float(d["h"]),
            "e": float(d["e"]),
            "m": float(d["m"]),
            "difficulty": difficulty,
            "base_plane": "XY",
        }
        return params

    def validate_params(self, params: dict) -> bool:
        d1, d2, d3, d4, h, e = (params[k] for k in ("d1", "d2", "d3", "d4", "h", "e"))
        if not (0 < d4 < d3):
            return False
        if d2 <= d1 or d2 >= d3:
            return False
        if h <= e + (d3 - d4) / 2:
            return False
        if params["m"] <= 0 or params["m"] >= d2:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1, shank_l = params["d1"], params["l"]
        d2, d3, d4 = params["d2"], params["d3"], params["d4"]
        h, e, m = params["h"], params["e"], params["m"]

        minor_R = round((d3 - d4) / 4.0, 3)
        major_R = round((d3 + d4) / 4.0, 3)
        eye_center_z = round(h - d3 / 2.0, 3)
        ring_bottom_z = round(eye_center_z - minor_R, 3)

        neck_base_d = round(min(m * 1.5, d2 * 0.8), 3)
        neck_top_z = round(ring_bottom_z - minor_R, 3)

        tags = {
            "has_hole": True,  # eye ring hole
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # 1. Collar (z = 0 .. e)
        ops = [
            Op("circle", {"radius": round(d2 / 2, 3)}),
            Op("extrude", {"distance": round(e, 3)}),
        ]
        # 2. Shank (z = -l .. 0) — union via sub-op (separate body below collar)
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, -shank_l], "rotate": [0, 0, 0]},
                        },
                        {"name": "circle", "args": {"radius": round(d1 / 2, 3)}},
                        {"name": "extrude", "args": {"distance": round(shank_l, 3)}},
                    ]
                },
            )
        )
        # 3. Neck (loft from collar-top to eye-bottom)
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, e], "rotate": [0, 0, 0]},
                        },
                        {
                            "name": "circle",
                            "args": {"radius": round(neck_base_d / 2, 3)},
                        },
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, neck_top_z - e],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "circle", "args": {"radius": round(m / 2, 3)}},
                        {"name": "loft", "args": {"combine": True}},
                    ]
                },
            )
        )
        # 4. Eye ring (torus with axis Y at eye_center_z)
        ops.append(
            Op(
                "torus",
                {
                    "majorRadius": major_R,
                    "minorRadius": minor_R,
                    "pnt": [0, 0, eye_center_z],
                    "dir": [0, 1, 0],
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
