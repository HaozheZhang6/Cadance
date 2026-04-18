"""Circlip (retaining ring) — DIN 471 (external) / DIN 472 (internal).

ISO 464 / DIN 471: External circlip for shafts — C-shaped ring, fits in shaft groove.
DIN 472: Internal circlip for bores — fits in bore groove.

Geometry: thin annular ring with a radial gap (opening) + two lug holes for pliers.
  - ring_od: outer diameter of the ring
  - ring_id: inner diameter (determines ring width)
  - gap_angle: total arc of the opening gap (typically 30–50°)
  - thickness: axial thickness
  - lug_hole_d: diameter of plier holes

Easy:   plain C-ring (extrude arc profile → sweep or revolve with cut)
Medium: + lug holes on the ears
Hard:   + bevel on the outer edge (DIN chamfer)
"""
import math

from .base import BaseFamily
from ..pipeline.builder import Op, Program

# DIN 471 shaft sizes → (d1_nom, t nominal thickness, b ring width) — simplified
_DIN471_SHAFT_D = [8, 10, 12, 15, 17, 19, 20, 22, 24, 25, 28, 30, 35, 40, 45, 50, 55, 60, 70, 80]


class CirclipFamily(BaseFamily):
    name = "circlip"
    standard = "DIN 471/472"

    def sample_params(self, difficulty: str, rng) -> dict:
        shaft_d = float(rng.choice(_DIN471_SHAFT_D))

        # DIN 471 proportions: ring od ≈ shaft_d * 0.87, thickness ≈ shaft_d * 0.06
        ring_id = round(shaft_d * 0.87, 1)
        ring_width = round(max(1.5, shaft_d * 0.08), 2)
        ring_od = round(ring_id + 2 * ring_width, 1)
        thickness = round(max(1.0, shaft_d * 0.055), 2)
        gap_angle = round(rng.uniform(30, 50), 1)  # degrees of opening

        params = {
            "shaft_diameter": shaft_d,
            "ring_od": ring_od,
            "ring_id": ring_id,
            "ring_width": ring_width,
            "thickness": thickness,
            "gap_angle": gap_angle,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Lug holes for circlip pliers — at the ears
            lug_d = round(max(1.0, ring_width * 0.5), 2)
            params["lug_hole_diameter"] = lug_d

        if difficulty == "hard":
            bevel = round(thickness * 0.2, 2)
            params["bevel_length"] = bevel

        return params

    def validate_params(self, params: dict) -> bool:
        rod = params["ring_od"]
        rid = params["ring_id"]
        t = params["thickness"]
        gap = params["gap_angle"]
        rw = params["ring_width"]

        if rod <= rid or rw < 1.0 or t < 0.8:
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
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": False,  # not a full revolution
        }

        # Build C-ring as a 2D closed profile (top view) extruded by thickness t.
        # Profile: outer arc (CCW, long way round the back) + two ear edges + inner arc (CW).
        # Gap opens toward +X. Ears at ±half_gap from +X axis.
        gap_half_rad = math.radians(gap / 2)
        r_outer = round(rod / 2, 4)
        r_inner = round(rid / 2, 4)
        mid_r = round((r_outer + r_inner) / 2, 4)

        # Key points (all in XY plane, gap opens at +X)
        # Outer arc: from top-ear to bottom-ear going CCW around the back (-X side)
        ox_ear  = round(r_outer * math.cos(gap_half_rad), 4)
        oy_ear  = round(r_outer * math.sin(gap_half_rad), 4)
        # Outer arc midpoint at angle=180 (back of ring)
        ox_mid  = round(-r_outer, 4)
        # Inner arc midpoint at angle=180
        ix_mid  = round(-r_inner, 4)
        ix_ear  = round(r_inner * math.cos(gap_half_rad), 4)
        iy_ear  = round(r_inner * math.sin(gap_half_rad), 4)

        ops.append(Op("workplane", {"selector": "XY"}))
        # Start at top-outer ear
        ops.append(Op("moveTo", {"x": ox_ear, "y": oy_ear}))
        # Outer arc CCW to bottom-outer ear (long arc, through back)
        ops.append(Op("threePointArc", {
            "point1": [ox_mid, 0.0],
            "point2": [ox_ear, -oy_ear],
        }))
        # Line to bottom-inner ear
        ops.append(Op("lineTo", {"x": ix_ear, "y": -iy_ear}))
        # Inner arc CW back to top-inner ear (through back, reversed direction)
        ops.append(Op("threePointArc", {
            "point1": [ix_mid, 0.0],
            "point2": [ix_ear, iy_ear],
        }))
        # Close back to start (top-outer ear)
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": t}))

        # Lug holes (medium+) at each ear tip — small cylinders cut through thickness
        lug_d = params.get("lug_hole_diameter", 0)
        if lug_d:
            tags["has_hole"] = True
            # Ears are the ends of the C-ring, at ±half_gap from +X axis
            ear_x = round(mid_r * math.cos(gap_half_rad), 4)
            ear_y = round(mid_r * math.sin(gap_half_rad), 4)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("moveTo", {"x": ear_x, "y": ear_y}))
            ops.append(Op("hole", {"diameter": round(lug_d, 4)}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("moveTo", {"x": ear_x, "y": -ear_y}))
            ops.append(Op("hole", {"diameter": round(lug_d, 4)}))

        # Bevel on outer edge (hard)
        bevel = params.get("bevel_length", 0)
        if bevel:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": round(bevel, 4)}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
