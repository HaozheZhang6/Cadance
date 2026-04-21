"""Keyhole hanger plate — furniture/frame hanging hardware.

Flat plate with a keyhole slot (large circle + narrow slot below) that accepts
a screw head: slide head through large opening, drop into narrow slot to lock.
Two or four mounting screw holes on the sides.

Keys: D (large hole diameter), d (narrow slot width), hole_pitch (screw centers).

Easy:   square plate + single keyhole.
Medium: + two mounting screw holes.
Hard:   larger plate + chamfered edges + four mounting holes.

Reference: No formal ISO/DIN — common hardware pattern (see Häfele 267 series).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class KeyholePlateFamily(BaseFamily):
    name = "keyhole_plate"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        D = round(rng.uniform(8.0, 16.0), 1)
        d_slot = round(D * rng.uniform(0.45, 0.6), 1)
        slot_drop = round(D * rng.uniform(1.0, 1.6), 1)  # center-to-center
        plate_w = round(D * 2.6, 1)
        plate_h = round(D + slot_drop + D * 1.8, 1)
        plate_t = round(rng.uniform(1.5, 3.5), 1)

        params = {
            "keyhole_D": D,
            "slot_width_d": d_slot,
            "slot_drop": slot_drop,
            "plate_width": plate_w,
            "plate_height": plate_h,
            "plate_thickness": plate_t,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["screw_hole_d"] = round(rng.uniform(3.0, 5.0), 1)
            params["screw_pitch"] = round(plate_w * 0.7, 1)
        if difficulty == "hard":
            params["edge_chamfer"] = round(plate_t * 0.25, 1)
            params["screw_count"] = 4
        else:
            params["screw_count"] = 2 if difficulty == "medium" else 0
        return params

    def validate_params(self, params: dict) -> bool:
        D = params["keyhole_D"]
        d = params["slot_width_d"]
        drop = params["slot_drop"]
        pw = params["plate_width"]
        ph = params["plate_height"]
        pt = params["plate_thickness"]
        if D < 6 or d <= 1 or d >= D:
            return False
        if drop < D * 0.8:
            return False
        if pw < D * 2 or ph < D + drop + D:
            return False
        if pt < 1.0:
            return False
        sp = params.get("screw_pitch", 0)
        sh = params.get("screw_hole_d", 0)
        if sp and sp + sh >= pw:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        D = params["keyhole_D"]
        d = params["slot_width_d"]
        drop = params["slot_drop"]
        pw = params["plate_width"]
        ph = params["plate_height"]
        pt = params["plate_thickness"]

        tags = {
            "has_hole": True,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Plate centered at origin in XY, extruded along Z
        ops = [
            Op("rect", {"length": round(pw, 3), "width": round(ph, 3)}),
            Op("extrude", {"distance": round(pt, 3)}),
        ]

        # Keyhole: big circle at top-center + vertical slot below
        big_r = round(D / 2, 3)
        top_cy = round(ph / 2 - D * 0.9, 3)  # circle center
        slot_bot_cy = round(top_cy - drop, 3)
        # Large circle cut
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, top_cy, pt / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(pt + 2, 3), "radius": big_r},
                        },
                    ]
                },
            )
        )
        # Narrow slot cut (rounded rect) from slot_bot_cy to top_cy
        slot_len = round(drop, 3)
        slot_cy = round((top_cy + slot_bot_cy) / 2, 3)
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, slot_cy, pt / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "slot2D",
                            "args": {
                                "length": slot_len,
                                "width": round(d, 3),
                                "angle": 90,
                            },
                        },
                        {
                            "name": "extrude",
                            "args": {"distance": round(pt + 2, 3), "both": True},
                        },
                    ]
                },
            )
        )

        # Screw mounting holes (medium/hard)
        sh = params.get("screw_hole_d")
        sp = params.get("screw_pitch")
        sc = params.get("screw_count", 0)
        if sh and sp and sc:
            if sc == 2:
                pts = [(sp / 2, -ph / 2 + D * 0.7), (-sp / 2, -ph / 2 + D * 0.7)]
            else:  # 4
                pts = [
                    (sp / 2, -ph / 2 + D * 0.7),
                    (-sp / 2, -ph / 2 + D * 0.7),
                    (sp / 2, ph / 2 - D * 0.6),
                    (-sp / 2, ph / 2 - D * 0.6),
                ]
            for px, py in pts:
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [px, py, pt / 2],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(pt + 2, 3),
                                        "radius": round(sh / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        # Edge chamfer (hard)
        ch = params.get("edge_chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
