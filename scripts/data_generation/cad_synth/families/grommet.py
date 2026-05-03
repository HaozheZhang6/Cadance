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
        # Asymmetric flange split (was 50/50). flange_top_ratio ∈ [0.3, 0.7].
        flange_top_ratio = round(float(rng.uniform(0.3, 0.7)), 3)
        profile_reverse = bool(rng.random() < 0.5)
        params = {
            "bore_d1": float(d1),
            "groove_d2": float(d2),
            "flange_d3": float(d3),
            "groove_width_w": float(w),
            "total_height_H": float(H),
            "flange_top_ratio": flange_top_ratio,
            "profile_reverse": profile_reverse,
            "difficulty": difficulty,
        }
        # Outer flange edge mod (top/bottom rim circles): chamfer or fillet
        # 50% medium / 70% hard (was unused in build path)
        rim_prob = {"easy": 0.2, "medium": 0.5, "hard": 0.75}[difficulty]
        if rng.random() < rim_prob:
            params["rim_op"] = str(rng.choice(["chamfer", "fillet"]))
            params["rim_size"] = round(float(rng.uniform(0.2, min(0.8, w * 0.4))), 2)
            params["rim_which"] = str(rng.choice(["top", "bottom", "both"]))
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
        # Asymmetric split: top flange = (H-w) · top_ratio, bottom = (H-w) · (1-ratio)
        ftr = float(params.get("flange_top_ratio", 0.5))
        flange_bot_h = round((H - w) * (1 - ftr), 4)
        flange_top_h = round((H - w) * ftr, 4)
        z0 = 0.0
        z_gb = flange_bot_h
        z_gt = flange_bot_h + w
        z1 = round(flange_bot_h + w + flange_top_h, 4)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # H-profile in XZ plane (u=radius, v=z), closed polyline revolved 360°
        # around world Z axis (axisEnd=(0,1,0) local = world Z per codebase).
        forward_pts = [
            (r1, z0),
            (r3, z0),
            (r3, z_gb),
            (r2, z_gb),
            (r2, z_gt),
            (r3, z_gt),
            (r3, z1),
            (r1, z1),
        ]
        pts = (
            list(reversed(forward_pts))
            if params.get("profile_reverse", False)
            else forward_pts
        )
        ops = [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {
                    "angleDeg": 360,
                    "axisStart": [0, 0, 0],
                    "axisEnd": [0, 1, 0],
                },
            )
        )

        # Optional outer flange rim chamfer/fillet on top/bottom outer-circle edge.
        # base_plane=XZ → faces(">Y") remaps to faces(">Z") world (top); "<Y" → "<Z".
        rim_op = params.get("rim_op")
        rim_size = float(params.get("rim_size", 0.0))
        rim_which = params.get("rim_which", "top")
        if rim_op and rim_size > 0:
            tags["has_chamfer"] = rim_op == "chamfer"
            tags["has_fillet"] = rim_op == "fillet"
            face_sels = []
            if rim_which in ("top", "both"):
                face_sels.append(">Y")
            if rim_which in ("bottom", "both"):
                face_sels.append("<Y")
            for sel in face_sels:
                ops.append(Op("faces", {"selector": sel}))
                ops.append(Op("edges", {}))
                if rim_op == "chamfer":
                    ops.append(Op("chamfer", {"length": rim_size}))
                else:
                    ops.append(Op("fillet", {"radius": rim_size}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
            base_plane="XZ",
        )
