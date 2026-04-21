"""Taper pin — ISO 2339 (unhardened, 1:50 taper).

Precision tapered pin for locking components on shafts.
Taper: 1:50 on diameter (d_small = d_nominal, d_large = d_nominal + l/50).
Length sampled within ISO 2339 range for each nominal diameter.

Easy:   plain tapered cylinder
Medium: + chamfer on large end
Hard:   + threaded extraction hole on large end (blind, tapped)

Reference: ISO 2339:1986 — Taper pins, unhardened; Table (d_nom, l_min, l_max for d 0.6–50mm)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 2339 taper pin 1:50 — (d_nominal, l_min, l_max) mm
_ISO2339 = [
    (1, 4, 20),
    (1.2, 4, 25),
    (1.5, 6, 32),
    (2, 6, 50),
    (2.5, 8, 63),
    (3, 10, 80),
    (4, 12, 100),
    (5, 14, 125),
    (6, 18, 160),
    (8, 22, 200),
    (10, 28, 260),
    (12, 32, 300),
    (16, 40, 400),
    (20, 50, 500),
]
_SMALL = [r for r in _ISO2339 if r[0] <= 5]
_MID = [r for r in _ISO2339 if 3 <= r[0] <= 12]
_ALL = _ISO2339


class TaperPinFamily(BaseFamily):
    """ISO 2339 taper pin, 1:50 taper."""

    name = "taper_pin"
    standard = "ISO 2339"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        d_nom, l_min, l_max = pool[int(rng.integers(0, len(pool)))]

        _len = [
            4,
            5,
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
        valid = [l for l in _len if l_min <= l <= l_max]
        length = float(valid[int(rng.integers(0, len(valid)))])

        # 1:50 taper: d_large = d_nom + length/50
        d_large = round(d_nom + length / 50, 3)

        params = {
            "d_nominal": float(d_nom),
            "d_large": d_large,
            "length": length,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(min(0.5, d_nom * 0.08), 2)

        if difficulty == "hard":
            # Tapped extraction hole on large end (M-thread, depth=1.5d)
            m_size = max(3.0, round(d_nom * 0.6, 0))
            params["extraction_thread_m"] = m_size
            params["extraction_depth"] = round(m_size * 1.5, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        d = params["d_nominal"]
        l = params["length"]
        dl = params["d_large"]
        if d < 1 or l < 4 or dl <= d:
            return False
        ext = params.get("extraction_depth", 0)
        if ext and ext >= l * 0.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d_nom = params["d_nominal"]
        d_lg = params["d_large"]
        l = params["length"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Tapered cylinder via revolve of trapezoid profile in XZ plane
        # Points: (r_small, 0) → (r_large, l) → (0, l) → (0, 0)
        r_s = round(d_nom / 2, 4)
        r_l = round(d_lg / 2, 4)
        ops.append(Op("workplane", {"selector": "XZ"}))
        ops.append(Op("moveTo", {"x": r_s, "y": 0.0}))
        ops.append(Op("lineTo", {"x": r_l, "y": l}))
        ops.append(Op("lineTo", {"x": 0.0, "y": l}))
        ops.append(Op("lineTo", {"x": 0.0, "y": 0.0}))
        ops.append(Op("close", {}))
        ops.append(Op("revolve", {"angleDeg": 360}))

        ch = params.get("chamfer_length")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": round(ch, 3)}))

        # Tapped extraction hole (hard)
        ext_m = params.get("extraction_thread_m")
        ext_d = params.get("extraction_depth")
        if ext_m and ext_d:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op(
                    "hole",
                    {"diameter": round(ext_m * 0.85, 2), "depth": round(ext_d, 2)},
                )
            )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
