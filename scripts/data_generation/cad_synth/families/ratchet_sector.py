"""Sector plate — circular sector (pie wedge) wire-EDM plate.

A flat plate cut to a circular sector shape: two straight radius edges + one arc edge.
Typical for indexing plates, ratchet sectors, angle brackets.

Easy:   plain solid sector extrude.
Medium: + through hole at apex + holes along arc.
Hard:   + radial lightening slots.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class RatchetSectorFamily(BaseFamily):
    name = "ratchet_sector"

    def sample_params(self, difficulty: str, rng) -> dict:
        outer_r = round(rng.uniform(30, 100), 1)
        angle_deg = round(rng.uniform(40, 150), 1)
        thick = round(rng.uniform(4, 16), 1)

        params = {
            "outer_radius": outer_r,
            "angle_deg": angle_deg,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            inner_r = round(rng.uniform(outer_r * 0.15, outer_r * 0.35), 1)
            params["inner_radius"] = inner_r
            n_holes = int(rng.choice([2, 3, 4]))
            hole_d = round(rng.uniform(3, max(3.5, min(8, outer_r * 0.08))), 1)
            params["arc_holes"] = n_holes
            params["hole_diameter"] = hole_d

        if difficulty == "hard":
            n_slots = int(rng.choice([2, 3]))
            params["n_slots"] = n_slots
            slot_w = round(rng.uniform(3, max(3.5, min(8, outer_r * 0.1))), 1)
            params["slot_width"] = slot_w

        return params

    def validate_params(self, params: dict) -> bool:
        r = params["outer_radius"]
        ang = params["angle_deg"]
        thick = params["thickness"]

        if r < 20:
            return False
        if ang < 30 or ang > 160:
            return False
        if thick < 3:
            return False

        ir = params.get("inner_radius", 0)
        if ir and ir >= r * 0.45:
            return False

        hd = params.get("hole_diameter", 0)
        if hd and hd >= r * 0.15:
            return False

        sw = params.get("slot_width", 0)
        if sw and sw >= r * 0.2:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        R = params["outer_radius"]
        ang = params["angle_deg"]
        thick = params["thickness"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Sector profile: from origin, out to (R, 0), arc to (R*cos(ang), R*sin(ang)), back.
        ang_rad = math.radians(ang)
        half_rad = math.radians(ang / 2)
        mid_x = round(R * math.cos(half_rad), 4)
        mid_y = round(R * math.sin(half_rad), 4)
        end_x = round(R * math.cos(ang_rad), 4)
        end_y = round(R * math.sin(ang_rad), 4)

        ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
        ops.append(Op("lineTo", {"x": round(R, 4), "y": 0.0}))
        ops.append(
            Op("threePointArc", {"point1": [mid_x, mid_y], "point2": [end_x, end_y]})
        )
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": round(thick, 4)}))

        # Apex hole + arc holes (medium+)
        ir = params.get("inner_radius")
        hd = params.get("hole_diameter")
        n_holes = params.get("arc_holes", 0)
        if ir and hd and n_holes:
            tags["has_hole"] = True
            # Apex hole at origin
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(0.0, 0.0)]}))
            ops.append(Op("hole", {"diameter": round(2 * ir, 4)}))

            # Arc holes at radius (R*0.7) evenly spaced within sector
            arc_r = round(R * 0.68, 4)
            step = ang / (n_holes + 1)
            pts = []
            for k in range(1, n_holes + 1):
                a_k = math.radians(step * k)
                pts.append(
                    (round(arc_r * math.cos(a_k), 4), round(arc_r * math.sin(a_k), 4))
                )
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": pts}))
            ops.append(Op("hole", {"diameter": round(hd, 4)}))

        # Radial lightening slots (hard)
        n_slots = params.get("n_slots", 0)
        sw = params.get("slot_width")
        if n_slots and sw:
            slot_len = round(R * 0.45, 4)
            slot_r = round(R * 0.45, 4)
            step = ang / (n_slots + 1)
            for k in range(1, n_slots + 1):
                a_k = math.radians(step * k)
                cx = round(slot_r * math.cos(a_k), 4)
                cy = round(slot_r * math.sin(a_k), 4)
                rot_deg = round(math.degrees(a_k), 2)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [cx, cy, 0.0],
                                        "rotate": [0, 0, rot_deg],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(slot_len, 4),
                                        "width": round(sw, 4),
                                        "height": round(thick + 1, 4),
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
