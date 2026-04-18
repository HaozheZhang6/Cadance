"""Clevis pin — ISO 2340 (without head).

Precision cylindrical pin for clevis/fork joints. Length sampled from
within the ISO 2340 table range for the chosen diameter.

Easy:   plain cylinder + chamfered ends
Medium: + cross-hole for split pin (ISO 1234)
Hard:   + groove near end for snap ring (circlip groove)

Reference: ISO 2340:1986 — Clevis pins without head; Table (d, l_min, l_max for d 3–50mm)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 2340 clevis pin without head — (d_nominal, l_min, l_max) mm
_ISO2340 = [
    (4, 10, 100),
    (5, 12, 120),
    (6, 14, 140),
    (8, 18, 180),
    (10, 22, 220),
    (12, 28, 260),
    (14, 32, 300),
    (16, 36, 340),
    (18, 40, 380),
    (20, 45, 420),
    (22, 50, 460),
    (24, 56, 500),
    (27, 63, 500),
    (30, 70, 500),
    (36, 90, 500),
    (40, 100, 500),
]
_SMALL = [r for r in _ISO2340 if r[0] <= 12]
_MID = [r for r in _ISO2340 if 8 <= r[0] <= 24]
_ALL = _ISO2340

# ISO 1234 split pin diameters by clevis pin diameter (approx mapping)
_SPLIT_PIN_D = {
    4: 1.0,
    5: 1.2,
    6: 1.6,
    8: 2.0,
    10: 2.5,
    12: 3.2,
    14: 3.2,
    16: 4.0,
    18: 4.0,
    20: 5.0,
    22: 5.0,
    24: 6.3,
    27: 6.3,
    30: 8.0,
    36: 8.0,
    40: 10.0,
}


class ClevisPinFamily(BaseFamily):
    """ISO 2340 clevis pin without head."""

    name = "clevis_pin"
    standard = "ISO 2340"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        d, l_min, l_max = pool[int(rng.integers(0, len(pool)))]

        # Pick length from preferred series within range
        _len = [
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
        valid = [l for l in _len if l_min <= l <= l_max]
        length = float(valid[int(rng.integers(0, len(valid)))])
        chamfer = round(min(1.0, d * 0.1), 1)

        params = {
            "diameter": float(d),
            "length": length,
            "chamfer_length": chamfer,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Cross-hole for split pin, positioned near pin end
            sp_d = _SPLIT_PIN_D.get(d, round(d * 0.2, 1))
            params["split_pin_diameter"] = sp_d
            # Hole centre at ~10% from end (or at least d/2+2 from end)
            params["split_pin_offset"] = round(max(d / 2 + 2, length * 0.1), 1)

        if difficulty == "hard":
            # Circlip groove near the other end
            params["groove_width"] = round(d * 0.12, 1)
            params["groove_depth"] = round(d * 0.06, 1)
            params["groove_offset"] = round(max(d / 2 + 3, length * 0.12), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        d = params["diameter"]
        l = params["length"]
        if d < 4 or l < d * 1.5:
            return False
        sp = params.get("split_pin_diameter", 0)
        if sp and sp >= d * 0.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["diameter"]
        l = params["length"]
        ch = params.get("chamfer_length", 0)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": bool(ch),
            "rotational": True,
        }

        ops.append(Op("cylinder", {"height": l, "radius": round(d / 2, 4)}))

        if ch:
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": round(ch, 3)}))

        # Cross-hole for split pin (medium+)
        sp_d = params.get("split_pin_diameter")
        sp_off = params.get("split_pin_offset")
        if sp_d and sp_off:
            tags["has_hole"] = True
            # Drill radially through pin at sp_off from bottom
            ops.append(Op("workplane", {"selector": "XZ"}))
            ops.append(Op("moveTo", {"x": 0, "y": round(sp_off - l / 2, 3)}))
            ops.append(Op("circle", {"radius": round(sp_d / 2, 3)}))
            ops.append(Op("cutThruAll", {}))

        # Circlip groove (hard)
        gw = params.get("groove_width")
        gd = params.get("groove_depth")
        g_off = params.get("groove_offset")
        if gw and gd and g_off:
            tags["has_slot"] = True
            inner_r = round(d / 2 - gd, 3)
            # Revolve a small rect around axis at groove position
            ops.append(Op("workplane", {"selector": "XZ"}))
            ops.append(Op("moveTo", {"x": inner_r, "y": round(l / 2 - g_off, 3)}))
            ops.append(Op("rect", {"length": gd, "width": gw}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
