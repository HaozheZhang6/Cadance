"""Spacer ring — precision adjustment shim (DIN 988 Passscheiben).

DIN 988: thin flat rings for axial adjustment of bearings, shaft collars, etc.
All (d, D) pairs and thickness series taken from DIN 988 Table 1 — exact values only.

Table: (d_bore, D_outer)  — thickness s sampled from standard series for each d.
Thickness series:
  d < 10  mm: s ∈ {0.1, 0.2, 0.3, 0.5}
  d 10–18 mm: s ∈ {0.1, 0.2, 0.3, 0.5, 0.8, 1.0}
  d ≥ 20  mm: s ∈ {0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0}

Easy:   plain flat ring (d ≤ 20)
Medium: plain flat ring, larger size range (d ≤ 50)
Hard:   split shim — full ring with narrow radial slit for snap-on
          installation without shaft disassembly (full d range; non-DIN variant)

Reference: DIN 988:1990 — Shim rings; Table (bore d, OD D, thickness s series for d 3–200mm)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 988 Table 1 — exact nominal (d_bore, D_outer) pairs, mm
_DIN988 = [
    (3, 7),
    (4, 9),
    (5, 10),
    (6, 11),
    (8, 14),
    (10, 18),
    (12, 20),
    (15, 24),
    (17, 26),
    (20, 30),
    (25, 37),
    (30, 42),
    (35, 47),
    (40, 52),
    (50, 65),
    (60, 75),
    (70, 90),
    (80, 100),
    (100, 120),
]

_S_THIN = [0.1, 0.2, 0.3, 0.5]  # d < 10
_S_MID = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0]  # d 10–18
_S_FULL = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0]  # d ≥ 20

_SMALL = [r for r in _DIN988 if r[0] <= 20]  # d 3–20
_MID = [r for r in _DIN988 if r[0] <= 50]  # d 3–50
_ALL = _DIN988  # d 3–100


def _thickness_series(d: float):
    if d < 10:
        return _S_THIN
    elif d < 20:
        return _S_MID
    else:
        return _S_FULL


class SpacerRingFamily(BaseFamily):
    name = "spacer_ring"
    standard = "DIN 988"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        d, D = pool[int(rng.integers(0, len(pool)))]
        s_opts = _thickness_series(float(d))
        s = float(s_opts[int(rng.integers(0, len(s_opts)))])

        params = {
            "bore_diameter": float(d),
            "outer_diameter": float(D),
            "thickness": s,
            "difficulty": difficulty,
        }

        if difficulty == "hard":
            # Split ring: ring is cut in half for installation without shaft disassembly
            params["split"] = True

        return params

    def validate_params(self, params: dict) -> bool:
        d = params["bore_diameter"]
        D = params["outer_diameter"]
        s = params["thickness"]
        if D <= d or s <= 0 or (D - d) / 2 < 1.0:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["bore_diameter"]
        D = params["outer_diameter"]
        s = params["thickness"]
        split = params.get("split", False)

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": not split,
        }

        r_outer = round(D / 2, 4)
        r_inner = round(d / 2, 4)

        # Plain flat ring: cylinder with through bore
        ops.append(Op("cylinder", {"height": s, "radius": r_outer}))
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(d, 4)}))

        if split:
            # Narrow radial slit through ring wall — snap-on installation
            tags["has_slot"] = True
            gap_w = round(max(0.8, min(2.5, (D - d) / 4)), 2)
            cut_center_x = round((r_outer + r_inner) / 2, 3)
            cut_len = round(D - d + 1, 3)
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [cut_center_x, 0.0, 0.0],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": cut_len,
                                    "width": gap_w,
                                    "height": round(s + 1, 3),
                                    "centered": True,
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
