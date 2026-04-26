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


def _hex_polyline_pts(ac: float) -> list:
    """6 vertices of a regular hexagon with circumscribed-circle diameter ac.
    First vertex on +X axis, going CCW."""
    r = ac / 2.0
    pts = []
    for i in range(6):
        ang = math.radians(60 * i)
        pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    return pts


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

        # Code-syntax diversity (Tier B style):
        # polygon_form: "polygon" (single op) vs "polyline" (6 lineTo's)
        # edge_op: chamfer / fillet / none — already had chamfer for med+
        # edge_loc: where to apply — "vertical" (|Z), "top" (>Z), "bottom" (<Z), "both"
        params["polygon_form"] = str(rng.choice(["polygon", "polyline"]))
        edge_prob = {"easy": 0.2, "medium": 0.85, "hard": 0.95}[difficulty]
        if rng.random() < edge_prob:
            params["edge_op"] = str(rng.choice(["chamfer", "fillet"]))
            params["edge_loc"] = str(rng.choice(["vertical", "top", "bottom", "both"]))
            # Face-based loc includes bore edge — scale size down (chamfer/fillet
            # of both outer-hex and inner-bore can collide for large radii).
            base = min(m * 0.15, 2.0)
            cap = base if params["edge_loc"] == "vertical" else min(base, M * 0.18)
            params["edge_size"] = round(cap, 2)
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

        es = params.get("edge_size", 0)
        if es and es >= h * 0.4:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ac = params["across_corners"]
        h = params["height"]
        bore = params["bore_diameter"]

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # Hex prism — polygon op or 6× lineTo polyline (geometry equivalent).
        polygon_form = params.get("polygon_form", "polygon")
        if polygon_form == "polygon":
            ops.append(Op("polygon", {"n": 6, "diameter": ac}))
        else:
            pts = _hex_polyline_pts(ac)
            ops.append(Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}))
            for x, y in pts[1:]:
                ops.append(Op("lineTo", {"x": x, "y": y}))
            ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": h}))

        # Central bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": round(bore / 2, 4)}))
        ops.append(Op("cutThruAll", {}))

        # Edge mod (medium+) — chamfer or fillet on vertical/top/bottom/both edges.
        edge_op = params.get("edge_op")
        edge_loc = params.get("edge_loc", "vertical")
        edge_size = float(params.get("edge_size", 0.0))
        if edge_op and edge_size > 0:
            if edge_op == "chamfer":
                tags["has_chamfer"] = True
            else:
                tags["has_fillet"] = True
            selectors = {
                "vertical": ["|Z"],
                "top": [">Z"],
                "bottom": ["<Z"],
                "both": [">Z", "<Z"],
            }[edge_loc]
            for sel in selectors:
                if sel.startswith("|"):
                    ops.append(Op("edges", {"selector": sel}))
                else:
                    ops.append(Op("faces", {"selector": sel}))
                    ops.append(Op("edges", {}))
                if edge_op == "chamfer":
                    ops.append(Op("chamfer", {"length": edge_size}))
                else:
                    ops.append(Op("fillet", {"radius": edge_size}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
