"""Clevis pin — ISO 2340 (without head).

Precision cylindrical pin for clevis/fork joints. Length sampled from
within the ISO 2340 table range for the chosen diameter.

Easy:   plain cylinder + chamfered ends                   (ISO 2340 type A)
Medium: + 1 cross-hole for split pin (ISO 1234) near end  (ISO 2340 type B, 1×)
Hard:   + 2 cross-holes (one each end) — true type B      (ISO 2340 type B, 2×)

ISO 2340 covers only type A (plain) and type B (with split-pin hole).
Circlip retention is a different standard (DIN 1444 type/E, DIN 471) and
is NOT included here to keep the family standard-pure.

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
        valid = [ln for ln in _len if l_min <= ln <= l_max]
        length = float(valid[int(rng.integers(0, len(valid)))])
        chamfer = round(min(1.0, d * 0.1), 1)

        params = {
            "diameter": float(d),
            "length": length,
            "chamfer_length": chamfer,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Cross-hole for split pin, positioned near pin end (ISO 2340 type B)
            sp_d = _SPLIT_PIN_D.get(d, round(d * 0.2, 1))
            params["split_pin_diameter"] = sp_d
            # Hole centre offset from bottom end: at least d/2+2, ~10% length
            params["split_pin_offset"] = round(max(d / 2 + 2, length * 0.1), 1)

        if difficulty == "hard":
            # Type B with 2 cross-holes — second hole near the OPPOSITE end
            params["split_pin_offset_2"] = round(max(d / 2 + 2, length * 0.1), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        d = params["diameter"]
        ln = params["length"]
        if d < 4 or ln < d * 1.5:
            return False
        sp = params.get("split_pin_diameter", 0)
        if sp and sp >= d * 0.5:
            return False
        # 2 cross-holes must not overlap: gap ≥ d
        sp1 = params.get("split_pin_offset", 0)
        sp2 = params.get("split_pin_offset_2", 0)
        if sp2 and (ln - sp1 - sp2) < d:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["diameter"]
        ln = params["length"]
        ch = params.get("chamfer_length", 0)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": bool(ch),
            "rotational": True,
        }

        ops.append(Op("cylinder", {"height": ln, "radius": round(d / 2, 4)}))

        if ch:
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": round(ch, 3)}))

        # Cross-holes for split pin (medium = 1 hole, hard = 2 holes)
        # Cylinder is centered at origin, axis along Z, so z spans -ln/2..+ln/2.
        # Drill radially: cut a Y-axis cylinder at z=hole_z (rotate=[90,0,0]
        # makes local Z align with world -Y, so the cylinder built on this
        # workplane has its axis along Y → cuts diametrically through the pin).
        sp_d = params.get("split_pin_diameter")
        sp_off = params.get("split_pin_offset")
        if sp_d and sp_off:
            tags["has_hole"] = True
            hole_z = round(-ln / 2 + sp_off, 3)
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, hole_z],
                                    "rotate": [90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(d * 1.5, 3),
                                    "radius": round(sp_d / 2, 3),
                                },
                            },
                        ]
                    },
                )
            )

        # Second cross-hole near top end (hard)
        sp_off_2 = params.get("split_pin_offset_2")
        if sp_d and sp_off_2:
            hole_z_2 = round(ln / 2 - sp_off_2, 3)
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, hole_z_2],
                                    "rotate": [90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(d * 1.5, 3),
                                    "radius": round(sp_d / 2, 3),
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
