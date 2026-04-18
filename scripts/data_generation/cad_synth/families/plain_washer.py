"""Washer — ISO 7089 (plain) / ISO 7090 (chamfered OD).

Difficulty controls geometry complexity:
  Easy:   plain flat ring (ISO 7089), M5–M20 preferred sizes
  Medium: + 45° OD chamfer (ISO 7090), full preferred range M5–M64
  Hard:   chamfered, includes non-preferred sizes (harder to ID exact size)

Dimensions from ISO 7090 Table 1 only — no continuous sampling.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 7090 Table 1 — exact nominal values (mm)
# (nominal_size, d1_clearance_bore, d2_outer_dia, h_thickness, preferred)
_ISO7090_TABLE = [
    (5, 5.30, 10.0, 1.0, True),
    (6, 6.40, 12.0, 1.6, True),
    (8, 8.40, 16.0, 1.6, True),
    (10, 10.50, 21.0, 2.0, True),
    (12, 13.00, 24.0, 2.5, True),
    (14, 15.00, 28.0, 2.5, False),
    (16, 17.00, 30.0, 3.0, True),
    (18, 19.00, 34.0, 3.0, False),
    (20, 21.00, 37.0, 3.0, True),
    (22, 23.00, 39.0, 3.0, False),
    (24, 25.00, 44.0, 4.0, True),
    (27, 28.00, 50.0, 4.0, False),
    (30, 31.00, 56.0, 4.0, True),
    (33, 34.00, 60.0, 5.0, False),
    (36, 37.00, 64.8, 5.0, True),
    (39, 42.00, 72.0, 6.0, False),
    (42, 45.00, 78.0, 8.0, True),
    (45, 48.00, 85.0, 8.0, False),
    (48, 52.00, 92.0, 8.0, True),
    (52, 56.00, 98.0, 8.0, False),
    (56, 62.00, 105.0, 10.0, True),
    (60, 66.00, 110.0, 10.0, False),
    (64, 70.00, 115.0, 10.0, True),
]

_SMALL = [r for r in _ISO7090_TABLE if r[4] and r[0] <= 20]  # M5–M20 preferred
_PREFERRED = [r for r in _ISO7090_TABLE if r[4]]  # M5–M64 preferred
_ALL = _ISO7090_TABLE  # all 23 rows


class WasherFamily(BaseFamily):
    """ISO 7089/7090 washer — plain (easy) or chamfered OD (medium/hard)."""

    name = "washer"
    standard = "ISO 7089"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _SMALL
        elif difficulty == "medium":
            pool = _PREFERRED
        else:
            pool = _ALL

        nominal, d1, d2, h, preferred = pool[int(rng.integers(0, len(pool)))]

        params = {
            "nominal_size": nominal,
            "bore_diameter": d1,
            "outer_diameter": d2,
            "thickness": h,
            "preferred": preferred,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # ISO 7090 chamfer: ~0.3×h, min 0.3 mm
            params["chamfer_length"] = round(max(0.3, h * 0.25), 2)

        return params

    def validate_params(self, params: dict) -> bool:
        d1 = params["bore_diameter"]
        d2 = params["outer_diameter"]
        h = params["thickness"]
        ch = params.get("chamfer_length", 0)
        if not (d2 > d1 > 0 and h > 0):
            return False
        if (d2 - d1) / 2 <= h * 0.1:
            return False
        if ch and (ch >= h * 0.5 or ch >= (d2 - d1) / 4):
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1 = params["bore_diameter"]
        d2 = params["outer_diameter"]
        h = params["thickness"]
        ch = params.get("chamfer_length")

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": bool(ch),
            "rotational": True,
        }

        ops.append(Op("cylinder", {"height": h, "radius": round(d2 / 2, 4)}))
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(d1, 4)}))

        if ch:
            # chamfer outer top edge (|Z selector = vertical/radial edges)
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": round(ch, 4)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )


# Keep old names as aliases so registry doesn't break during transition
PlainWasherFamily = WasherFamily
ChamferedWasherFamily = WasherFamily
