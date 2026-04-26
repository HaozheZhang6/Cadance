"""Shaft collar — cylindrical ring with central bore (DIN 705 Form A).

Dimensions from DIN 705 Table 1: bore_d → (od, width_b).
Easy:   small bores M6–M25 — ring + center bore
Medium: mid bores M16–M50 — + chamfer rims + radial set screw hole
Hard:   full range M6–M100 — + raised hub variant

Reference: DIN 705:1994 — Shaft collars; Table (bore d, OD, width for d 10–120mm)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

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

        # Edge fillet/chamfer + setscrew + hub all spread cross-difficulty.
        edge_prob = {"easy": 0.3, "medium": 0.7, "hard": 0.85}[difficulty]
        if rng.random() < edge_prob:
            params["chamfer_length"] = round(rng.uniform(0.4, min(2.0, width / 6)), 1)
            params["edge_op"] = str(rng.choice(["fillet", "chamfer"]))
            params["edge_loc"] = str(rng.choice([">Z", "<Z", "both"]))
        screw_prob = {"easy": 0.0, "medium": 0.6, "hard": 0.7}[difficulty]
        if rng.random() < screw_prob:
            sd = round(rng.uniform(2.0, max(2.1, min(5.0, (od - bore_d) / 6))), 1)
            params["screw_diameter"] = sd
            # Variable setscrew count: 1, 2, 3 around 360°
            params["screw_count"] = int(rng.choice([1, 1, 2, 3]))
        hub_prob = {"easy": 0.0, "medium": 0.2, "hard": 0.6}[difficulty]
        if rng.random() < hub_prob:
            hub_lo = bore_d * 1.4
            hub_hi = od * 0.75
            hub_od = round(rng.uniform(hub_lo, max(hub_lo + 1, hub_hi)), 1)
            hub_h = round(rng.uniform(width * 0.4, width * 0.85), 1)
            params["hub_diameter"] = hub_od
            params["hub_height"] = hub_h

        # Code-syntax: body cylinder/extrude + bore form
        params["body_form"] = str(rng.choice(["cylinder", "extrude"]))
        params["bore_form"] = str(rng.choice(["hole", "cut"]))

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

        body_form = params.get("body_form", "cylinder")
        bore_form = params.get("bore_form", "hole")
        # Base ring
        if body_form == "cylinder":
            ops.append(
                Op("cylinder", {"height": round(w, 3), "radius": round(od / 2, 3)})
            )
        else:
            ops.append(Op("circle", {"radius": round(od / 2, 3)}))
            ops.append(Op("extrude", {"distance": round(w, 3)}))

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
        if bore_form == "hole":
            ops.append(Op("hole", {"diameter": round(bd, 3)}))
        else:
            ops.append(Op("circle", {"radius": round(bd / 2, 3)}))
            ops.append(Op("cutThruAll", {}))

        # Edge fillet/chamfer top/bottom rim (推 fillet 频率)
        cl = params.get("chamfer_length")
        edge_op = params.get("edge_op", "chamfer")
        edge_loc = params.get("edge_loc", ">Z")
        if cl:
            if edge_op == "fillet":
                tags["has_fillet"] = True
            else:
                tags["has_chamfer"] = True
            sels = {">Z": [">Z"], "<Z": ["<Z"], "both": [">Z", "<Z"]}[edge_loc]
            for sel in sels:
                ops.append(Op("edges", {"selector": sel}))
                if edge_op == "fillet":
                    ops.append(Op("fillet", {"radius": round(cl, 3)}))
                else:
                    ops.append(Op("chamfer", {"length": round(cl, 3)}))

        # Radial set screws — variable count around 360° (推 cut 频率)
        sd = params.get("screw_diameter")
        sn = int(params.get("screw_count", 1) or 0)
        if sd and sn:
            import math as _m

            for i in range(sn):
                ang_deg = 360.0 * i / sn
                ang_rad = _m.radians(ang_deg)
                # Cut a cylindrical hole radially at this angle
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0.0, 0.0, round(w / 2, 3)],
                                        "rotate": [90.0, 0.0, ang_deg],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(od + 4, 3),
                                        "radius": round(sd / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )
                _ = ang_rad

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
