"""Hex nut — ISO 4032 style hexagonal nut, M-series.

ISO 4032: Hexagon nuts, style 1 — product grades A and B.
Dimensions from ISO 4032 Table 1 (exact nominal values only).

Table: (M_nominal, s_across_flats, m_nut_height)
across-corners = s / cos(30°) — used as polygon diameter.
bore = M_nominal (thread minor diameter approximated as M for geometry).

Easy:   M3–M12; hex prism + thru bore.
Medium: M6–M24; + chamfer on top+bottom face edges.
Hard:   full range M3–M48; same chamfer.

Reference: ISO 4032:2012 — Hexagon regular nuts (style 1); Table 1 (M_nom, s, m for M1.6–M64)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 4032 Table 1 — exact nominal values (mm)
# (M_nominal, s_across_flats, m_nut_height)
_ISO4032 = [
    (3, 5.5, 2.4),
    (4, 7.0, 3.2),
    (5, 8.0, 4.7),
    (6, 10.0, 5.2),
    (8, 13.0, 6.8),
    (10, 16.0, 8.4),
    (12, 18.0, 10.8),
    (14, 21.0, 12.8),
    (16, 24.0, 14.8),
    (18, 27.0, 15.8),
    (20, 30.0, 18.0),
    (22, 34.0, 19.4),
    (24, 36.0, 21.5),
    (27, 41.0, 23.8),
    (30, 46.0, 25.6),
    (36, 55.0, 31.0),
    (42, 65.0, 34.0),
    (48, 75.0, 38.0),
]


class HexNutFamily(BaseFamily):
    """ISO 4032 hex nut."""

    name = "hex_nut"
    standard = "ISO 4032"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = [r for r in _ISO4032 if r[0] <= 12]
        elif difficulty == "medium":
            pool = [r for r in _ISO4032 if 6 <= r[0] <= 24]
        else:
            pool = _ISO4032

        M, s, m = pool[int(rng.integers(0, len(pool)))]

        # across-corners = s / cos(30°) for hex polygon
        across_corners = round(s / math.cos(math.radians(30)), 2)

        params = {
            "nominal_size": M,
            "across_flats": float(s),
            "across_corners": across_corners,
            "height": float(m),
            "bore_diameter": float(M),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(m * 0.15, 2.0), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        ac = params["across_corners"]
        h = params["height"]
        bore = params["bore_diameter"]

        if ac < 5 or ac > 90:
            return False
        if h < 2:
            return False
        if bore >= ac * 0.75:
            return False
        if bore < 3:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= h * 0.4:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ac = params["across_corners"]
        h = params["height"]
        bore = params["bore_diameter"]

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # Hex prism (across-corners = circumscribed circle diameter)
        ops.append(Op("polygon", {"n": 6, "diameter": ac}))
        ops.append(Op("extrude", {"distance": h}))

        # Central bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": round(bore / 2, 4)}))
        ops.append(Op("cutThruAll", {}))

        # Chamfer 6 vertical hex edges (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
