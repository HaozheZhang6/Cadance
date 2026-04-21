"""Grommet — H-profile cable/wire protective bushing (rubber/plastic).

H-profile revolved 360° around Z axis: inner bore for cable, circumferential
groove mating the panel hole, top and bottom flanges that retain the grommet.

Keys: d1 (inner bore), d2 (groove diameter = panel hole), d3 (flange OD),
w (groove width, panel thickness nominal), H (overall height).

Easy:   simple H profile.
Medium: + rounded inner rim (fillet on inner edges of flange).
Hard:   + flange profile chamfered for easy insertion.

Reference: no active standard dim table used; dimensions are imperial-derived
values (1/8", 1/4", etc.) in the range typical of catalog grommets (McMaster
9600K series). MS 35489 and DIN 40621 cover the same part class but their
full tables were not transcribed here.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# MS 35489 sample dimensions — (d1_bore, d2_groove, d3_flange, w_groove, H_total)
_GROMMET_SIZES = [
    (3.2, 6.4, 9.5, 1.6, 4.8),
    (4.8, 7.9, 11.1, 2.0, 5.6),
    (6.4, 11.1, 14.3, 2.4, 7.1),
    (7.9, 12.7, 17.5, 2.4, 7.9),
    (9.5, 15.9, 20.6, 3.2, 9.5),
    (12.7, 19.1, 25.4, 3.2, 11.1),
    (15.9, 22.2, 28.6, 4.0, 12.7),
    (19.1, 28.6, 34.9, 4.0, 14.3),
]


class GrommetFamily(BaseFamily):
    name = "grommet"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _GROMMET_SIZES[:3]
        elif difficulty == "medium":
            pool = _GROMMET_SIZES[2:6]
        else:
            pool = _GROMMET_SIZES[4:]

        d1, d2, d3, w, H = pool[int(rng.integers(0, len(pool)))]
        params = {
            "bore_d1": float(d1),
            "groove_d2": float(d2),
            "flange_d3": float(d3),
            "groove_width_w": float(w),
            "total_height_H": float(H),
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["bore_fillet"] = round(min(d1 * 0.15, 0.8), 2)
        if difficulty == "hard":
            params["flange_chamfer"] = round((H - w) * 0.08, 2)
        return params

    def validate_params(self, params: dict) -> bool:
        d1 = params["bore_d1"]
        d2 = params["groove_d2"]
        d3 = params["flange_d3"]
        w = params["groove_width_w"]
        H = params["total_height_H"]
        if d2 <= d1 or d3 <= d2:
            return False
        if w >= H * 0.8:
            return False
        if H <= 1.0:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1 = params["bore_d1"]
        d2 = params["groove_d2"]
        d3 = params["flange_d3"]
        w = params["groove_width_w"]
        H = params["total_height_H"]

        r1 = round(d1 / 2, 4)
        r2 = round(d2 / 2, 4)
        r3 = round(d3 / 2, 4)
        flange_h = round((H - w) / 2, 4)  # each flange half
        z0 = 0.0
        z_gb = flange_h  # groove bottom z
        z_gt = flange_h + w  # groove top z
        z1 = H

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # H-profile in XZ plane (u=radius, v=z), closed polyline revolved 360°
        # around world Z axis (axisEnd=(0,1,0) local = world Z per codebase).
        ops = [
            Op("moveTo", {"x": r1, "y": z0}),
            Op("lineTo", {"x": r3, "y": z0}),
            Op("lineTo", {"x": r3, "y": z_gb}),
            Op("lineTo", {"x": r2, "y": z_gb}),
            Op("lineTo", {"x": r2, "y": z_gt}),
            Op("lineTo", {"x": r3, "y": z_gt}),
            Op("lineTo", {"x": r3, "y": z1}),
            Op("lineTo", {"x": r1, "y": z1}),
            Op("close", {}),
            Op(
                "revolve",
                {
                    "angleDeg": 360,
                    "axisStart": [0, 0, 0],
                    "axisEnd": [0, 1, 0],
                },
            ),
        ]

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
            base_plane="XZ",
        )
