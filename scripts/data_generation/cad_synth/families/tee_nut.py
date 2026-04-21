"""Tee nut — pronged T-nut for wood-threaded inserts.

Round flange (top) + cylindrical barrel extending down with a central threaded
bore + 3 or 4 triangular prongs on the flange underside that drive into wood.
Prongs modeled as tapered boxes via extrude(taper=...) trick.

Keys: d (thread), D (flange OD), H (barrel height), b (flange thickness),
prong_count (3 or 4).

Easy:   flange + barrel + through-bore, no prongs.
Medium: + 4 straight prongs on flange underside.
Hard:   + tapered prongs (extrude taper) + edge chamfer on flange OD.

Reference: no active standard (DIN 1624 withdrawn); dimensions follow common
vendor (McMaster/Tnutz) catalog proportions for M4..M12 nominal threads.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# (d_thread_M, D_flange, H_barrel, barrel_OD, b_flange_thick)
# Vendor catalog proportions (no active standard).
_TEENUT_SIZES = [
    (4.0, 18.0, 8.0, 7.0, 1.0),
    (5.0, 20.0, 9.0, 8.0, 1.2),
    (6.0, 22.0, 11.0, 9.0, 1.5),
    (8.0, 28.0, 13.0, 11.0, 1.5),
    (10.0, 32.0, 15.0, 13.0, 1.8),
    (12.0, 38.0, 18.0, 16.0, 2.0),
]


class TeeNutFamily(BaseFamily):
    name = "tee_nut"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _TEENUT_SIZES[:3]
        elif difficulty == "medium":
            pool = _TEENUT_SIZES[1:5]
        else:
            pool = _TEENUT_SIZES[3:]

        d, D, H, bd, b = pool[int(rng.integers(0, len(pool)))]
        params = {
            "thread_d": float(d),
            "flange_D": float(D),
            "barrel_H": float(H),
            "barrel_od": float(bd),
            "flange_t": float(b),
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["prong_count"] = 4
            params["prong_h"] = round(b * 2.5, 1)
            params["prong_w"] = round(b * 1.2, 1)
        if difficulty == "hard":
            params["flange_chamfer"] = round(b * 0.3, 2)
            params["prong_taper"] = 10.0  # degrees (tapered to tip)
        return params

    def validate_params(self, params: dict) -> bool:
        d = params["thread_d"]
        D = params["flange_D"]
        H = params["barrel_H"]
        bd = params["barrel_od"]
        b = params["flange_t"]
        if D <= bd + 2 or bd <= d + 1 or H < d * 0.8 or b < 0.8:
            return False
        ph = params.get("prong_h", 0)
        if ph and ph <= b:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["thread_d"]
        D = params["flange_D"]
        H = params["barrel_H"]
        bd = params["barrel_od"]
        b = params["flange_t"]

        r_thread = round(d / 2, 4)
        r_flange = round(D / 2, 4)
        r_barrel = round(bd / 2, 4)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout: flange at z=[0, b] (top), barrel extends DOWN to z=-H.
        # Build flange first (extrude up from z=0), then barrel as union
        # extending downward from z=0.
        ops = [
            Op("circle", {"radius": r_flange}),
            Op("extrude", {"distance": round(b, 4)}),
        ]
        # Barrel extending down from z=0 to z=-H (union)
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, -H / 2], "rotate": [0, 0, 0]},
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(H, 4), "radius": r_barrel},
                        },
                    ],
                },
            )
        )

        # Edge chamfer on flange OD (hard)
        ch = params.get("flange_chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Prongs on flange underside (medium+)
        pc = params.get("prong_count", 0)
        ph = params.get("prong_h")
        pw = params.get("prong_w")
        taper = params.get("prong_taper", 0)
        if pc and ph and pw:
            # Place on a circle just inside flange OD
            prong_r = (r_flange + r_barrel) / 2
            for i in range(pc):
                ang = 2 * math.pi * i / pc
                px = round(prong_r * math.cos(ang), 4)
                py = round(prong_r * math.sin(ang), 4)
                if taper:
                    # Tapered extrude: rect at flange base, tapered to point
                    ops.append(
                        Op(
                            "union",
                            {
                                "plane": "XY",
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [px, py, 0],
                                            "rotate": [0, 0, 0],
                                        },
                                    },
                                    {
                                        "name": "rect",
                                        "args": {
                                            "length": round(pw, 4),
                                            "width": round(pw, 4),
                                        },
                                    },
                                    {
                                        "name": "extrude",
                                        "args": {
                                            "distance": round(-ph, 4),
                                            "taper": taper,
                                        },
                                    },
                                ],
                            },
                        )
                    )
                else:
                    ops.append(
                        Op(
                            "union",
                            {
                                "plane": "XY",
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [px, py, -ph / 2],
                                            "rotate": [0, 0, 0],
                                        },
                                    },
                                    {
                                        "name": "box",
                                        "args": {
                                            "length": round(pw, 4),
                                            "width": round(pw, 4),
                                            "height": round(ph, 4),
                                        },
                                    },
                                ],
                            },
                        )
                    )

        # Through-bore along Z (central threaded hole, modeled as plain cylinder)
        ops.append(
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, (b - H) / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": round(H + b + 2, 4),
                                "radius": r_thread,
                            },
                        },
                    ],
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
