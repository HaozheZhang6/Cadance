"""Parallel key (feather key) — DIN 6885A Form A.

Rectangular precision key used to transmit torque between shaft and hub.
Dimensions from DIN 6885A Table 1: shaft_d range → (b, h, l_min, l_max).

Easy:   plain rectangular bar (b × h × l)
Medium: + chamfered ends (45° × 0.4mm)
Hard:   + slot along length (key with central oil groove)

Reference: DIN 6885A:1968 — Parallel keys, type A; Table (shaft_d range, b, h, l_min, l_max)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 6885A Form A — (shaft_d_min, shaft_d_max, b, h, l_min, l_max) mm
_DIN6885A = [
    (6, 8, 2, 2, 6, 20),
    (8, 10, 3, 3, 6, 36),
    (10, 12, 4, 4, 8, 45),
    (12, 17, 5, 5, 10, 56),
    (17, 22, 6, 6, 14, 70),
    (22, 30, 8, 7, 18, 90),
    (30, 38, 10, 8, 22, 110),
    (38, 44, 12, 8, 28, 140),
    (44, 50, 14, 9, 36, 160),
    (50, 58, 16, 10, 45, 180),
    (58, 65, 18, 11, 50, 200),
    (65, 75, 20, 12, 56, 220),
    (75, 85, 22, 14, 63, 250),
    (85, 95, 25, 14, 70, 280),
    (95, 110, 28, 16, 80, 320),
    (110, 130, 32, 18, 90, 360),
    (130, 150, 36, 20, 100, 400),
    (150, 170, 40, 22, 110, 400),
    (170, 200, 45, 25, 125, 450),
    (200, 230, 50, 28, 140, 500),
]

_SMALL = _DIN6885A[:7]  # shaft 6–38 mm
_MID = _DIN6885A[4:13]  # shaft 17–85 mm
_ALL = _DIN6885A


class ParallelKeyFamily(BaseFamily):
    """DIN 6885A Form A parallel key."""

    name = "parallel_key"
    standard = "DIN 6885"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        row = pool[int(rng.integers(0, len(pool)))]
        shaft_d_min, shaft_d_max, b, h, l_min, l_max = row

        # Pick a shaft diameter from the range (for reference/QA only)
        shaft_d = round(rng.uniform(shaft_d_min, shaft_d_max), 1)
        # Pick a standard length from preferred series within [l_min, l_max]
        _len_series = [
            6,
            8,
            10,
            12,
            14,
            16,
            18,
            20,
            22,
            25,
            28,
            32,
            36,
            40,
            45,
            50,
            56,
            63,
            70,
            80,
            90,
            100,
            110,
            125,
            140,
            160,
            180,
            200,
            220,
            250,
            280,
            320,
            360,
            400,
            450,
            500,
        ]
        valid_l = [l for l in _len_series if l_min <= l <= l_max]
        length = float(valid_l[int(rng.integers(0, len(valid_l)))])

        params = {
            "shaft_diameter": shaft_d,
            "key_width": float(b),
            "key_height": float(h),
            "key_length": length,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(min(0.6, b * 0.15), 2)

        if difficulty == "hard":
            # Central oil groove along key length
            params["groove_width"] = round(b * 0.3, 1)
            params["groove_depth"] = round(h * 0.2, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        b = params["key_width"]
        h = params["key_height"]
        l = params["key_length"]
        if b < 2 or h < 2 or l < 6:
            return False
        if l < b:
            return False
        gw = params.get("groove_width", 0)
        gd = params.get("groove_depth", 0)
        if gw and (gw >= b * 0.7 or gd >= h * 0.5):
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        b = params["key_width"]
        h = params["key_height"]
        l = params["key_length"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # Plain rectangular bar: length=l (X), width=b (Y), height=h (Z)
        ops.append(Op("box", {"length": l, "width": b, "height": h}))

        # Chamfer ends (medium+): chamfer the 4 edges on each end face (|X edges)
        ch = params.get("chamfer_length")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|X"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Oil groove (hard): slot along top face center
        gw = params.get("groove_width")
        gd = params.get("groove_depth")
        if gw and gd:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("rect", {"length": round(l * 0.8, 2), "width": gw}))
            ops.append(Op("cutBlind", {"depth": gd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
