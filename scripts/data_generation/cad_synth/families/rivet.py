"""Round-head rivet — DIN 660 / ISO 1051 round head rivet.

Cylindrical shank + spherical cap head. Head dims per DIN 660:
  d_k (head dia) ≈ 1.6·d, k (head height) ≈ 0.65·d.

Cap is modeled as a spherical cap: sphere radius r_sphere satisfies
  (d_k/2)² + (r - k)² = r²  →  r = ((d_k/2)² + k²) / (2·k)
Sphere centered at z = shank_L + k - r. Keep only the portion above
z = shank_L via revolved profile (axis Z, XZ-plane workplane).

Easy:   d ∈ {3, 4, 5}, shorter shank.
Medium: d ∈ {4, 5, 6, 8}, + chamfer on shank tip.
Hard:   d ∈ {8, 10, 12}, + tail-end flare for set/formed rivet look.

Reference: DIN 660:1988 — Rivet, round head.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 660 Tab.1 (selected) — (d_nominal, d_k, k)
_DIN660 = {
    3: {"d_k": 4.8, "k": 1.95},
    4: {"d_k": 6.4, "k": 2.6},
    5: {"d_k": 8.0, "k": 3.25},
    6: {"d_k": 9.6, "k": 3.9},
    8: {"d_k": 12.8, "k": 5.2},
    10: {"d_k": 16.0, "k": 6.5},
    12: {"d_k": 19.2, "k": 7.8},
}

_SHANK_L = [6, 8, 10, 12, 16, 20, 25, 30, 40, 50]


class RivetFamily(BaseFamily):
    name = "rivet"
    standard = "DIN 660"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = [3, 4, 5]
        elif difficulty == "medium":
            pool = [4, 5, 6, 8]
        else:
            pool = [8, 10, 12]
        d = int(rng.choice(pool))
        row = _DIN660[d]
        L_min = max(6, int(d * 2))
        L_max = min(50, int(d * 6))
        candidates = [L for L in _SHANK_L if L_min <= L <= L_max]
        L = float(rng.choice(candidates)) if candidates else float(L_min)

        params = {
            "d": float(d),
            "d_k": float(row["d_k"]),
            "k": float(row["k"]),
            "shank_length": L,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["tip_chamfer"] = round(d * 0.1, 2)
        return params

    def validate_params(self, params: dict) -> bool:
        d, d_k, k, L = params["d"], params["d_k"], params["k"], params["shank_length"]
        if d < 2 or d_k <= d or k <= 0 or L < d * 1.5:
            return False
        ch = params.get("tip_chamfer", 0)
        if ch and ch >= d * 0.3:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["d"]
        d_k = params["d_k"]
        k = params["k"]
        L = params["shank_length"]
        r_sh = round(d / 2, 3)
        r_head = round(d_k / 2, 3)
        sphere_r = round(((d_k / 2) ** 2 + k * k) / (2 * k), 4)
        dome_top = round(L + k, 3)

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Combined revolve profile on XZ plane — axis = Z (world):
        #   (0,0) → (d/2, 0) → (d/2, L) → (d_k/2, L) → arc to (0, L+k) → close.
        # ThreePointArc passes through a midpoint on the sphere between rim and apex.
        mid_x = round(r_head * 0.866, 4)  # cos 30°
        mid_z = round(L + k * 0.5, 4)
        ops = [
            Op("moveTo", {"x": 0.0, "y": 0.0}),
            Op("lineTo", {"x": r_sh, "y": 0.0}),
            Op("lineTo", {"x": r_sh, "y": round(L, 3)}),
            Op("lineTo", {"x": r_head, "y": round(L, 3)}),
            Op(
                "threePointArc",
                {"point1": [mid_x, mid_z], "point2": [0.0, dome_top]},
            ),
            Op("close"),
            Op(
                "revolve",
                {"angleDeg": 360, "axisStart": [0, 0, 0], "axisEnd": [0, 1, 0]},
            ),
        ]

        # Tip chamfer (medium+) on shank bottom circular edge
        ch = params.get("tip_chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Keep sphere_r for QA generator
        params["sphere_radius"] = sphere_r

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
            base_plane="XZ",
        )
