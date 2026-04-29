"""Lobed knob — generic N-lobe grip knob (non-standard).

Smooth flower-shape outline: central disc plus N large lobe circles
(radius = 0.55·R_outer) placed at radius (R_outer − lobe_r) from center,
unioned so lobes overlap smoothly. Central threaded bush protrudes below
the base.

This is a generic parametric knob — NOT a DIN 6336 Sterngriff. Real DIN
6336 knobs have specific silhouette curvature, top/bottom ergonomic
fillets, and catalog-exact proportions that this family does not match.
Use as non-standard training geometry.

Keys: d_thread (mm). Columns:
  d1     = overall tip-to-tip outer diameter
  h1     = total knob body height (above base)
  N      = number of lobes (3/5/6)
  bush_h = threaded bush height below knob base

Easy:   d=5–8, N=5 (small grip)
Medium: d=8–12, N=3/5/6
Hard:   d=10–16, N=3/5/6
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_DIMS = {
    5: {"d1": 32, "h1": 14, "bush_h": 6},
    6: {"d1": 40, "h1": 18, "bush_h": 8},
    8: {"d1": 50, "h1": 22, "bush_h": 10},
    10: {"d1": 63, "h1": 28, "bush_h": 12},
    12: {"d1": 80, "h1": 35, "bush_h": 15},
    16: {"d1": 100, "h1": 44, "bush_h": 18},
}


class LobedKnobFamily(BaseFamily):
    """Generic N-lobe grip knob (non-standard)."""

    name = "lobed_knob"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            thread_pool = [5, 6, 8]
            n_pool = [3, 4, 5]
        elif difficulty == "medium":
            thread_pool = [8, 10, 12]
            n_pool = [3, 4, 5, 6, 7]
        else:
            thread_pool = [10, 12, 16]
            n_pool = [3, 4, 5, 6, 7, 8]

        d = int(rng.choice(thread_pool))
        N = int(rng.choice(n_pool))
        row = _DIMS[d]

        lobe_r_ratio = round(float(rng.uniform(0.45, 0.62)), 3)
        core_r_off = round(float(rng.uniform(0.0, 1.5)), 2)

        params = {
            "d_thread": float(d),
            "d1": float(row["d1"]),
            "h1": float(row["h1"]),
            "N": N,
            "bush_h": float(row["bush_h"]),
            "lobe_r_ratio": lobe_r_ratio,
            "core_r_off": core_r_off,
            "difficulty": difficulty,
            "base_plane": "XY",
        }
        return params

    def validate_params(self, params: dict) -> bool:
        d, d1, h1, N, bush_h = (
            params[k] for k in ("d_thread", "d1", "h1", "N", "bush_h")
        )
        if d <= 0:
            return False
        if d1 < d * 3 or d1 > d * 20:
            return False
        if h1 <= 0 or h1 > d1:
            return False
        if N not in (3, 4, 5, 6, 7, 8):
            return False
        if bush_h <= 0 or bush_h > h1 * 1.5:
            return False
        if d * 2 >= d1 * 0.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d_thread = params["d_thread"]
        d1 = params["d1"]
        h1 = params["h1"]
        N = int(params["N"])
        bush_h = params["bush_h"]

        R_outer = d1 / 2
        lobe_r = round(R_outer * float(params.get("lobe_r_ratio", 0.55)), 3)
        R_inner = round(R_outer - lobe_r, 3)
        core_r = round(R_inner + float(params.get("core_r_off", 0.5)), 3)
        bush_d = round(d_thread * 2.0, 3)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        ops: list = []

        ops.append(Op("circle", {"radius": core_r}))
        ops.append(Op("extrude", {"distance": round(h1, 3)}))

        for i in range(N):
            ang = 2 * math.pi * i / N
            cx = round(R_inner * math.cos(ang), 3)
            cy = round(R_inner * math.sin(ang), 3)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {"offset": [cx, cy, 0]},
                            },
                            {"name": "circle", "args": {"radius": lobe_r}},
                            {"name": "extrude", "args": {"distance": round(h1, 3)}},
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
                            "args": {"offset": [0, 0, -bush_h]},
                        },
                        {"name": "circle", "args": {"radius": round(bush_d / 2, 3)}},
                        {"name": "extrude", "args": {"distance": round(bush_h, 3)}},
                    ]
                },
            )
        )

        full_h = round(h1 + bush_h + 2, 3)
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, -bush_h - 1]},
                        },
                        {"name": "circle", "args": {"radius": round(d_thread / 2, 3)}},
                        {"name": "extrude", "args": {"distance": full_h}},
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
