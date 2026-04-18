"""Circlip (retaining ring) — DIN 471 (external shaft) / DIN 472 (internal bore).

ISO 464 / DIN 471: External circlip for shafts — C-shaped ring, fits in shaft groove.
DIN 472: Internal circlip for bores — fits in bore groove.

Geometry: thin annular ring with a radial gap (opening) + two lug holes for pliers.
Dimensions from DIN 471 Table 1 — exact nominal values only (no continuous sampling).

Table: (d1_shaft, d3_ring_od, s_thickness)
  d1 = nominal shaft diameter [mm]
  d3 = ring outer diameter [mm]
  s  = axial ring thickness [mm]

Easy:   plain C-ring (d1 ≤ 25 mm)
Medium: + lug holes on the ears (d1 ≤ 50 mm)
Hard:   + bevel on outer edge (full range d1 8–80 mm)
"""

import math

from .base import BaseFamily
from ..pipeline.builder import Op, Program

# DIN 471 Table 1 — exact nominal values (d1_shaft, d3_ring_od, s_thickness) mm
_DIN471 = [
    (8, 13.8, 0.8),
    (10, 17.8, 1.0),
    (12, 20.5, 1.0),
    (14, 23.5, 1.0),
    (15, 24.5, 1.0),
    (16, 26.5, 1.0),
    (17, 28.0, 1.0),
    (18, 29.5, 1.0),
    (19, 31.0, 1.0),
    (20, 33.5, 1.2),
    (22, 36.5, 1.2),
    (24, 39.5, 1.5),
    (25, 40.5, 1.5),
    (28, 45.5, 1.5),
    (30, 48.5, 1.5),
    (35, 56.5, 1.75),
    (40, 64.5, 1.75),
    (45, 71.5, 2.0),
    (50, 80.5, 2.0),
    (55, 88.5, 2.0),
    (60, 97.5, 2.0),
    (70, 113.0, 2.5),
    (80, 129.0, 2.5),
]

_SMALL = [r for r in _DIN471 if r[0] <= 25]  # d1 8–25
_MID = [r for r in _DIN471 if r[0] <= 50]  # d1 8–50
_ALL = _DIN471  # d1 8–80


class CirclipFamily(BaseFamily):
    name = "circlip"
    standard = "DIN 471/472"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        d1, d3, s = pool[int(rng.integers(0, len(pool)))]

        ring_id = float(d1)
        ring_od = float(d3)
        thickness = float(s)
        ring_width = round((d3 - d1) / 2, 2)
        gap_angle = 35.0  # standard DIN 471 gap ≈ 35°

        params = {
            "shaft_diameter": float(d1),
            "ring_od": ring_od,
            "ring_id": ring_id,
            "ring_width": ring_width,
            "thickness": thickness,
            "gap_angle": gap_angle,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            lug_d = round(max(1.0, ring_width * 0.45), 2)
            params["lug_hole_diameter"] = lug_d

        if difficulty == "hard":
            params["bevel_length"] = round(thickness * 0.2, 2)

        return params

    def validate_params(self, params: dict) -> bool:
        rod = params["ring_od"]
        rid = params["ring_id"]
        t = params["thickness"]
        gap = params["gap_angle"]
        rw = params["ring_width"]

        if rod <= rid or rw < 1.0 or t < 0.5:
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
