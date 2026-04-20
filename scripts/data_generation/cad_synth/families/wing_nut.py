"""Wing nut — DIN 315 German-form butterfly nut (rounded wings).

Tapered hub (loft from d2 bottom to d2/3 top over height m) with two
symmetric ears extending ±X. Ear silhouette on XZ plane:
hub base (d2/2, 0) → 45° takeoff to outer tip (e/2, e/2-d2/2) → three-point
arc up to apex (e/4+d2/4, h) → inner drop to (d3/2, m) → back to center
(0, m). Extruded both=True with distance d3/8 (total Y thickness d3/4).

Arc derivation (per user-verified manual_wingnut.py):
  x_arc = e/4 + d2/4
  R     = (dX² + dZ²) / (2·dZ),  dX = e/2 - x_arc,  dZ = h - (e/2 - d2/2)
  Z_c   = h - R
  mid   = arc midpoint at angle (atan2(Z_end-Z_c, dX) + π/2) / 2

Keys: d_thread (mm). Columns (DIN 315 approx.):
  d2     = hub base outer diameter
  m      = hub height
  e      = ear tip-to-tip span
  h      = total height (ear peak)
  d3     = ear thickness driver (Y thickness = d3/4)
  hole_d = through-hole diameter

Easy:   M3–M6
Medium: M5–M10
Hard:   M8–M20

Reference: DIN 315:2018 rounded-wing form.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_DIN315 = {
    3: {"d2": 8, "m": 4, "e": 19, "h": 10, "d3": 6, "hole_d": 3.2},
    4: {"d2": 10, "m": 5, "e": 25, "h": 12, "d3": 8, "hole_d": 4.3},
    5: {"d2": 12, "m": 6, "e": 30, "h": 14, "d3": 10, "hole_d": 5.3},
    6: {"d2": 14, "m": 8, "e": 35, "h": 16, "d3": 11, "hole_d": 6.4},
    8: {"d2": 16, "m": 10, "e": 39, "h": 20, "d3": 12.5, "hole_d": 8.4},
    10: {"d2": 20, "m": 12, "e": 45, "h": 24, "d3": 16, "hole_d": 10.5},
    12: {"d2": 24, "m": 14, "e": 55, "h": 28, "d3": 20, "hole_d": 13.0},
    16: {"d2": 32, "m": 18, "e": 70, "h": 36, "d3": 26, "hole_d": 17.0},
    20: {"d2": 40, "m": 22, "e": 90, "h": 44, "d3": 32, "hole_d": 21.0},
}


def _ear_polyline_ops(
    sign, half_d2, X_end, Z_end, mid_x, mid_z, x_arc, h, half_d3, m, ear_half_t
):
    """Build ear polyline+extrude sub-ops.  sign = +1 for +X ear, -1 for -X."""
    return [
        {"name": "moveTo", "args": {"x": 0.0, "y": 0.0}},
        {"name": "lineTo", "args": {"x": sign * half_d2, "y": 0.0}},
        {"name": "lineTo", "args": {"x": sign * X_end, "y": Z_end}},
        {
            "name": "threePointArc",
            "args": {
                "point1": [sign * mid_x, mid_z],
                "point2": [sign * x_arc, h],
            },
        },
        {"name": "lineTo", "args": {"x": sign * half_d3, "y": m}},
        {"name": "lineTo", "args": {"x": 0.0, "y": m}},
        {"name": "close", "args": {}},
        {"name": "extrude", "args": {"distance": ear_half_t, "both": True}},
    ]


class WingNutFamily(BaseFamily):
    """DIN 315 butterfly wing nut with rounded ears."""

    name = "wing_nut"
    standard = "DIN 315"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = [3, 4, 5, 6]
        elif difficulty == "medium":
            pool = [5, 6, 8, 10]
        else:
            pool = [8, 10, 12, 16, 20]

        d = int(rng.choice(pool))
        row = _DIN315[d]
        params = {
            "d_thread": float(d),
            "d2": float(row["d2"]),
            "m": float(row["m"]),
            "e": float(row["e"]),
            "h": float(row["h"]),
            "d3": float(row["d3"]),
            "hole_d": float(row["hole_d"]),
            "difficulty": difficulty,
            "base_plane": "XY",
        }
        return params

    def validate_params(self, params: dict) -> bool:
        d, d2, m, e, h, d3, hole_d = (
            params[k] for k in ("d_thread", "d2", "m", "e", "h", "d3", "hole_d")
        )
        if d <= 0:
            return False
        if d2 < d + 1 or d2 > e * 0.6:
            return False
        if e < d2 * 1.4:
            return False
        if h <= m or m <= 0:
            return False
        if d3 <= 0 or d3 > d2:
            return False
        if hole_d <= 0 or hole_d > d2 - 2:
            return False
        if h <= (e / 2 - d2 / 2):
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d2 = params["d2"]
        m = params["m"]
        e = params["e"]
        h = params["h"]
        d3 = params["d3"]
        hole_d = params["hole_d"]

        x_arc = e / 4 + d2 / 4
        X_end = e / 2
        Z_end = e / 2 - d2 / 2
        dX = X_end - x_arc
        dZ = h - Z_end
        R = (dX * dX + dZ * dZ) / (2 * dZ)
        Z_c = h - R
        ang_start = math.atan2(Z_end - Z_c, X_end - x_arc)
        ang_end = math.pi / 2
        ang_mid = (ang_start + ang_end) / 2
        mid_x = x_arc + R * math.cos(ang_mid)
        mid_z = Z_c + R * math.sin(ang_mid)

        half_d2 = round(d2 / 2, 3)
        half_d3 = round(d3 / 2, 3)
        X_end_r = round(X_end, 3)
        Z_end_r = round(Z_end, 3)
        mid_x_r = round(mid_x, 3)
        mid_z_r = round(mid_z, 3)
        x_arc_r = round(x_arc, 3)
        mr = round(m, 3)
        hr = round(h, 3)
        ear_half_t = round(d3 / 8, 3)
        fillet_r = round(ear_half_t * 0.8, 3)
        hole_r = round(hole_d / 2, 3)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": True,
            "has_chamfer": False,
            "rotational": False,
        }

        ops: list = []

        # 1. Tapered hub: loft circle(d2/2) at z=0 → circle(d2/3) at z=m
        ops.append(Op("circle", {"radius": half_d2}))
        ops.append(Op("workplane_offset", {"offset": mr}))
        ops.append(Op("circle", {"radius": round(d2 / 3, 3)}))
        ops.append(Op("loft", {"combine": True}))

        # 2. +X ear on XZ plane (extrude both=True in ±Y)
        ops.append(
            Op(
                "union",
                {
                    "plane": "XZ",
                    "ops": _ear_polyline_ops(
                        1,
                        half_d2,
                        X_end_r,
                        Z_end_r,
                        mid_x_r,
                        mid_z_r,
                        x_arc_r,
                        hr,
                        half_d3,
                        mr,
                        ear_half_t,
                    ),
                },
            )
        )

        # 3. -X ear (mirror across YZ by negating X coords)
        ops.append(
            Op(
                "union",
                {
                    "plane": "XZ",
                    "ops": _ear_polyline_ops(
                        -1,
                        half_d2,
                        X_end_r,
                        Z_end_r,
                        mid_x_r,
                        mid_z_r,
                        x_arc_r,
                        hr,
                        half_d3,
                        mr,
                        ear_half_t,
                    ),
                },
            )
        )

        # 4. Through-hole
        ops.append(
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "transformed", "args": {"offset": [0, 0, -1]}},
                        {"name": "circle", "args": {"radius": hole_r}},
                        {"name": "extrude", "args": {"distance": round(m * 2 + 2, 3)}},
                    ],
                },
            )
        )

        # 5. Fillet ear perimeter edges (parallel to Y axis)
        ops.append(Op("edges", {"selector": "|Y"}))
        ops.append(Op("fillet", {"radius": fillet_r}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
