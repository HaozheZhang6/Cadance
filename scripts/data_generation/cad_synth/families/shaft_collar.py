"""Shaft collar — cylindrical ring with central bore (DIN 705 Form A).

Dimensions from DIN 705 Table 1: bore_d → (od, width_b).
Easy:   small bores M6–M25 — ring + center bore
Medium: mid bores M16–M50 — + chamfer rims + radial set screw hole
Hard:   full range M6–M100 — + raised hub variant
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program

# DIN 705 Form A shaft collar — (bore_d, od, width_b) mm
_DIN705 = [
    (6, 12, 8),
    (8, 16, 8),
    (10, 20, 10),
    (12, 22, 12),
    (14, 25, 12),
    (15, 25, 12),
    (16, 28, 12),
    (18, 32, 14),
    (20, 32, 14),
    (22, 36, 14),
    (25, 40, 16),
    (28, 45, 16),
    (30, 45, 16),
    (35, 56, 16),
    (40, 63, 18),
    (45, 70, 18),
    (50, 80, 18),
    (55, 80, 18),
    (60, 90, 20),
    (65, 100, 20),
    (70, 100, 20),
    (80, 110, 22),
    (90, 125, 22),
    (100, 140, 25),
]
_SMALL = [r for r in _DIN705 if r[0] <= 25]
_MID = [r for r in _DIN705 if 16 <= r[0] <= 50]
_ALL = _DIN705


class ShaftCollarFamily(BaseFamily):
    name = "shaft_collar"
    standard = "DIN 705"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        bore_d, od, width = pool[int(rng.integers(0, len(pool)))]

        params = {
            "bore_diameter": float(bore_d),
            "outer_diameter": float(od),
            "width": float(width),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            cl = round(rng.uniform(0.4, min(2.0, width / 6)), 1)
            sd = round(rng.uniform(2.0, max(2.1, min(5.0, (od - bore_d) / 6))), 1)
            params["chamfer_length"] = cl
            params["screw_diameter"] = sd

        if difficulty == "hard":
            hub_lo = bore_d * 1.4
            hub_hi = od * 0.75
            hub_od = round(rng.uniform(hub_lo, max(hub_lo + 1, hub_hi)), 1)
            hub_h = round(rng.uniform(width * 0.4, width * 0.85), 1)
            params["hub_diameter"] = hub_od
            params["hub_height"] = hub_h

        return params

    def validate_params(self, params: dict) -> bool:
        bd = params["bore_diameter"]
        od = params["outer_diameter"]
        w = params["width"]
        if od <= bd * 1.3 or bd < 6 or w < 4 or od < 12:
            return False
        sd = params.get("screw_diameter")
        if sd and sd >= (od - bd) / 4:
            return False
        hub_od = params.get("hub_diameter")
        hub_h = params.get("hub_height")
        if hub_od:
            if hub_od <= bd * 1.2 or hub_od >= od * 0.9:
                return False
            if hub_h and hub_h >= w:
                return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bd = params["bore_diameter"]
        od = params["outer_diameter"]
        w = params["width"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Base ring
        ops.append(Op("cylinder", {"height": round(w, 3), "radius": round(od / 2, 3)}))

        # Hard: union hub on top (raised smaller cylinder, same bore)
        hub_od = params.get("hub_diameter")
        hub_h = params.get("hub_height")
        if hub_od and hub_h:
            z_ctr = round(w / 2 + hub_h / 2 - 0.5, 3)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, z_ctr],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(hub_h, 3),
                                    "radius": round(hub_od / 2, 3),
                                },
                            },
                        ]
                    },
                )
            )

        # Center bore (axial, thru entire part)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(bd, 3)}))

        # Chamfer top rim (medium+)
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": round(cl, 3)}))

        # Radial set screw hole on side — drill through diameter in Y direction
        sd = params.get("screw_diameter")
        if sd:
            # XZ plane at Z=0 (mid-height), hole goes radially through in Y
            ops.append(Op("workplane", {"selector": "XZ"}))
            ops.append(Op("pushPoints", {"points": [[0, 0]]}))
            ops.append(Op("hole", {"diameter": round(sd, 3)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
