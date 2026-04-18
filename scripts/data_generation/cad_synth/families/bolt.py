"""Hex-head bolt — hexagonal head + cylindrical shaft.

ISO 4014 / ISO 4017 hex head bolts, M-series per ISO 261.
Dimensions from ISO 4014 Table 1 (partial thread) — exact standard values only.

Table: (M_nominal, s_across_flats, k_head_height)
Standard lengths sampled from ISO 888 preferred length series.
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program

# ISO 4014 Table 1 — hex bolt dimensions (exact values, mm)
# (M_nominal, s_across_flats, k_head_height)
_ISO4014 = [
    (3,   5.5,  2.0),
    (4,   7.0,  2.8),
    (5,   8.0,  3.5),
    (6,   10.0, 4.0),
    (8,   13.0, 5.3),
    (10,  17.0, 6.4),
    (12,  19.0, 7.5),
    (14,  22.0, 8.8),
    (16,  24.0, 10.0),
    (18,  27.0, 11.5),
    (20,  30.0, 12.5),
    (22,  34.0, 14.0),
    (24,  36.0, 15.0),
    (27,  41.0, 17.0),
    (30,  46.0, 18.7),
    (36,  55.0, 22.5),
    (42,  65.0, 26.0),
    (48,  75.0, 30.0),
]

# ISO 888 preferred length series (mm)
_ISO888_LENGTHS = [8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60,
                   65, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160,
                   180, 200, 220, 240, 260, 280, 300]


class BoltFamily(BaseFamily):
    name = "bolt"
    standard = "ISO 4014"

    def sample_params(self, difficulty: str, rng) -> dict:
        # Difficulty controls M-size range
        if difficulty == "easy":
            pool = [r for r in _ISO4014 if r[0] <= 12]
        elif difficulty == "medium":
            pool = [r for r in _ISO4014 if 6 <= r[0] <= 24]
        else:
            pool = _ISO4014

        M, s, k = pool[int(rng.integers(0, len(pool)))]

        # Pick length from ISO 888 series: at least 2.5×M, at most 10×M
        valid_lens = [l for l in _ISO888_LENGTHS if M * 2.5 <= l <= M * 10]
        if not valid_lens:
            valid_lens = [round(M * 4)]
        shaft_len = float(valid_lens[int(rng.integers(0, len(valid_lens)))])

        # across-corners = s / cos(30°) for hex
        head_d = round(s / math.cos(math.radians(30)), 2)

        params = {
            "nominal_size": M,
            "across_flats": float(s),
            "shaft_diameter": float(M),
            "shaft_length": shaft_len,
            "head_diameter": head_d,
            "head_height": float(k),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(k * 0.15, 1.5), 1)

        if difficulty == "hard":
            # ISO 4014 thread length per standard (approx b = 2M + 6 for M≤125mm)
            thread_l = round(min(2 * M + 6, shaft_len * 0.6), 1)
            params["thread_length"] = thread_l
            params["thread_relief"] = round(M * 0.05, 2)

        return params

    def validate_params(self, params: dict) -> bool:
        M = params["shaft_diameter"]
        hd = params["head_diameter"]
        hh = params["head_height"]
        sl = params["shaft_length"]

        if M < 3 or sl < M * 2:
            return False
        if hd < M * 1.5 or hd > M * 2.6:
            return False
        if hh < 1.5:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= hh * 0.4:
            return False

        tl = params.get("thread_length", 0)
        if tl and tl >= sl * 0.8:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        M = params["shaft_diameter"]
        sl = params["shaft_length"]
        hd = params["head_diameter"]
        hh = params["head_height"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Hex head: polygon(6) + extrude upward from z=0
        ops.append(Op("polygon", {"n": 6, "diameter": hd}))
        ops.append(Op("extrude", {"distance": hh}))

        # Chamfer top edge of head (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Shaft: union cylinder below head (centered at z = -sl/2)
        shaft_center_z = round(-sl / 2, 4)
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, shaft_center_z],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": sl, "radius": round(M / 2, 4)},
                        },
                    ]
                },
            )
        )

        # Thread section: reduced-diameter cylinder at shaft tip (hard)
        tl = params.get("thread_length")
        tr = params.get("thread_relief", 0)
        if tl and tr:
            # Cut a thin annulus from the threaded portion to show reduced diameter
            thread_center_z = round(-sl + tl / 2, 4)
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, thread_center_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(tl, 4),
                                    "radius": round(M / 2, 4),
                                },
                            },
                        ]
                    },
                )
            )
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, thread_center_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(tl, 4),
                                    "radius": round((M - tr * 2) / 2, 4),
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
