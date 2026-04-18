"""Snap disc / E-ring retaining ring — DIN 6799 (Sicherungsscheiben für Wellen).

DIN 6799: Flat disc-type retaining rings for shaft grooves — smaller and more
disc-like than DIN 471 circlips. Snaps into an annular groove on a shaft.
Shaft range d = 1.5–24 mm; fits into a groove that is ≈ 0.1–0.2 mm narrower.

Geometry: flat C-ring (two concentric arcs with gap), plier holes in the ears.
All (d_shaft, d1_bore, D_outer, s_thickness) from DIN 6799 Table 1 — exact values.

Easy:   plain C-ring (d ≤ 8 mm)
Medium: + lug holes for snap-ring pliers (d ≤ 17 mm)
Hard:   + chamfered outer edge (full range d 1.5–24 mm)

Reference: DIN 6799:1981 — Circlips (E-rings) for shafts; Table (d_shaft, d1, D, s for d 1.5–40mm)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 6799 Table 1 — exact nominal (d_shaft, d1_bore, D_outer, s_thickness) mm
_DIN6799 = [
    (1.5, 1.3, 3.3, 0.4),
    (2.0, 1.8, 4.4, 0.4),
    (2.5, 2.2, 5.5, 0.5),
    (3.0, 2.7, 6.5, 0.6),
    (4.0, 3.7, 8.5, 0.7),
    (5.0, 4.7, 10.5, 0.8),
    (6.0, 5.6, 13.0, 0.9),
    (7.0, 6.6, 15.0, 1.0),
    (8.0, 7.6, 17.0, 1.0),
    (9.0, 8.6, 19.0, 1.1),
    (10.0, 9.6, 21.0, 1.2),
    (12.0, 11.5, 24.0, 1.2),
    (14.0, 13.5, 27.0, 1.5),
    (15.0, 14.5, 28.0, 1.5),
    (17.0, 16.5, 32.0, 1.7),
    (19.0, 18.5, 36.0, 2.0),
    (20.0, 19.5, 38.0, 2.0),
    (24.0, 23.5, 44.0, 2.5),
]

_SMALL = [r for r in _DIN6799 if r[0] <= 8]  # d 1.5–8
_MID = [r for r in _DIN6799 if r[0] <= 17]  # d 1.5–17
_ALL = _DIN6799  # d 1.5–24


class SnapClipFamily(BaseFamily):
    name = "snap_clip"
    standard = "DIN 6799"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        d, d1, D, s = pool[int(rng.integers(0, len(pool)))]

        ring_width = round((D - d1) / 2, 3)
        gap_angle = 35.0  # DIN 6799 standard gap ≈ 35°

        params = {
            "shaft_diameter": float(d),
            "ring_id": float(d1),
            "ring_od": float(D),
            "thickness": float(s),
            "ring_width": ring_width,
            "gap_angle": gap_angle,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            lug_d = round(max(0.5, ring_width * 0.4), 2)
            params["lug_hole_diameter"] = lug_d

        if difficulty == "hard":
            params["bevel_length"] = round(s * 0.2, 2)

        return params

    def validate_params(self, params: dict) -> bool:
        rod = params["ring_od"]
        rid = params["ring_id"]
        t = params["thickness"]
        gap = params["gap_angle"]
        rw = params["ring_width"]

        if rod <= rid or rw < 0.3 or t < 0.3:
            return False
        if gap < 20 or gap > 60:
            return False

        lug_d = params.get("lug_hole_diameter", 0)
        if lug_d and lug_d >= rw * 0.8:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rod = params["ring_od"]
        rid = params["ring_id"]
        t = params["thickness"]
        gap = params["gap_angle"]
        rw = params["ring_width"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        gap_half_rad = math.radians(gap / 2)
        r_outer = round(rod / 2, 4)
        r_inner = round(rid / 2, 4)
        mid_r = round((r_outer + r_inner) / 2, 4)

        ox_ear = round(r_outer * math.cos(gap_half_rad), 4)
        oy_ear = round(r_outer * math.sin(gap_half_rad), 4)
        ox_mid = round(-r_outer, 4)
        ix_mid = round(-r_inner, 4)
        ix_ear = round(r_inner * math.cos(gap_half_rad), 4)
        iy_ear = round(r_inner * math.sin(gap_half_rad), 4)

        ops.append(Op("workplane", {"selector": "XY"}))
        ops.append(Op("moveTo", {"x": ox_ear, "y": oy_ear}))
        ops.append(
            Op("threePointArc", {"point1": [ox_mid, 0.0], "point2": [ox_ear, -oy_ear]})
        )
        ops.append(Op("lineTo", {"x": ix_ear, "y": -iy_ear}))
        ops.append(
            Op("threePointArc", {"point1": [ix_mid, 0.0], "point2": [ix_ear, iy_ear]})
        )
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": t}))

        lug_d = params.get("lug_hole_diameter", 0)
        if lug_d:
            tags["has_hole"] = True
            ear_x = round(mid_r * math.cos(gap_half_rad), 4)
            ear_y = round(mid_r * math.sin(gap_half_rad), 4)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("moveTo", {"x": ear_x, "y": ear_y}))
            ops.append(Op("hole", {"diameter": round(lug_d, 4)}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("moveTo", {"x": ear_x, "y": -ear_y}))
            ops.append(Op("hole", {"diameter": round(lug_d, 4)}))

        bevel = params.get("bevel_length", 0)
        if bevel:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": round(bevel, 4)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
