"""Torsion spring — DIN 2088 helical wound spring with two tangent legs.

Three independent solids unioned (matches tmp/manual_family_previews/manual_torsion_spring.py):
  1. Main coil  : sweep circle(wr) along helix(pitch, height, R) on tilted
                  start plane (perpendicular to start tangent).
  2. Leg1       : circle(wr) extruded backwards (-leg_len) on the same
                  start plane → tangent to coil at t=0.
  3. Leg2       : circle(wr) extruded forwards (+leg_len) on tilted plane
                  at the helix end (R, 0, H) → tangent at t=2π·n.

Integer n_coils ⇒ end tangent direction equals start tangent direction
(only origin shifts by (0, 0, H)). No assembleEdges, no spline fit, no
Frenet seam at leg/helix junction — three pure solids unioned.

Plane rotation: start tangent = (0, R, p/(2π))/mag → rotate XY plane about
its X axis by α = -atan2(R, p/(2π)) so plane normal aligns with tangent.

DIN 2088:1992 parameters; DIN 2095 wire series. Spring index c = D/d.
Pitch p > 1.2·wire_d to keep coils open and avoid OCC kernel deadlock.

Easy:   small wire d 0.8–2.5 mm, c=6–12, 3–6 coils
Medium: mid wire 1.6–4.0 mm, c=5–14, 3–8 coils
Hard:   heavy wire 2.5–8.0 mm, c=4–16, 4–12 coils

Reference: DIN 2088:1992 — Torsion springs (Schenkelfedern).
           DIN 2095:1973 — Wire series.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_SMALL_D = [0.8, 1.0, 1.25, 1.6, 2.0, 2.5]
_MID_D = [1.6, 2.0, 2.5, 3.15, 4.0]
_ALL_D = [2.5, 3.15, 4.0, 5.0, 6.3, 8.0]


class TorsionSpringFamily(BaseFamily):
    name = "torsion_spring"
    standard = "DIN 2088"

    def sample_params(self, difficulty: str, rng) -> dict:
        d_pool = (
            _SMALL_D
            if difficulty == "easy"
            else (_MID_D if difficulty == "medium" else _ALL_D)
        )
        wire_d = float(d_pool[int(rng.integers(0, len(d_pool)))])
        wire_r = wire_d / 2

        if difficulty == "easy":
            c = float(rng.choice([6, 7, 8, 10, 12]))
            n_coils = int(rng.choice([3, 4, 5, 6]))
        elif difficulty == "medium":
            c = float(rng.choice([5, 6, 8, 10, 12, 14]))
            n_coils = int(rng.choice([3, 4, 5, 6, 7, 8]))
        else:
            c = float(rng.choice([4, 5, 6, 8, 10, 12, 14, 16]))
            n_coils = int(rng.choice([4, 5, 6, 7, 8, 9, 10, 12]))

        coil_r = round(c * wire_d / 2, 2)
        # pitch must be > wire_d (open coil) — manual recommends ≥ 2·wire_d
        pitch = round(wire_d * rng.uniform(2.0, 3.5), 2)
        height = round(pitch * n_coils, 6)
        leg_len_1 = round(coil_r * rng.uniform(1.5, 3.0), 1)
        # Asymmetric legs (was symmetric): leg2 = leg1 × ratio.
        leg_ratio = round(float(rng.uniform(0.7, 1.3)), 2)
        leg_len_2 = round(leg_len_1 * leg_ratio, 1)
        leg_order_swap = bool(rng.random() < 0.5)

        return {
            "wire_diameter": wire_d,
            "wire_radius": round(wire_r, 3),
            "spring_index": c,
            "coil_radius": coil_r,
            "mean_coil_diameter": round(coil_r * 2, 3),
            "n_coils": float(n_coils),
            "pitch": pitch,
            "height": height,
            "leg_length": leg_len_1,  # leg1 (back-compat key for QA gen)
            "leg_length_2": leg_len_2,
            "leg_ratio": leg_ratio,
            "leg_order_swap": leg_order_swap,
            "difficulty": difficulty,
            "base_plane": "XY",
        }

    def validate_params(self, params: dict) -> bool:
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        wd = params["wire_diameter"]
        p = params["pitch"]
        h = params["height"]
        ll = params["leg_length"]
        ll2 = params.get("leg_length_2", ll)

        if wr < 0.25:
            return False
        c = cr / wr if wr > 0 else 0
        if not (3.8 <= c <= 16.5):
            return False
        if p < wd * 1.5:
            return False
        if h < 5 or h > 400:
            return False
        if ll < cr or ll > cr * 4:
            return False
        if ll2 < cr * 0.7 or ll2 > cr * 5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        p = params["pitch"]
        h = params["height"]
        ll1 = params["leg_length"]
        ll2 = params.get("leg_length_2", ll1)
        leg_order_swap = bool(params.get("leg_order_swap", False))

        # Plane rotation about X so plane normal = start tangent direction.
        # tangent = (0, R, p/(2π))/mag; rot_x = -atan2(R, p/(2π))
        rot_x = round(-math.degrees(math.atan2(cr, p / (2 * math.pi))), 4)

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Main coil: tilted start plane → circle → sweep helix.
        ops = [
            Op("transformed", {"offset": [cr, 0, 0], "rotate": [rot_x, 0, 0]}),
            Op("circle", {"radius": wr}),
            Op(
                "sweep",
                {
                    "path_type": "helix",
                    "path_args": {"pitch": p, "height": h, "radius": cr},
                    "isFrenet": True,
                },
            ),
        ]
        # Leg1 — extrude opposite to start tangent (negative)
        leg1 = Op(
            "union",
            {
                "ops": [
                    {
                        "name": "transformed",
                        "args": {"offset": [cr, 0, 0], "rotate": [rot_x, 0, 0]},
                    },
                    {"name": "circle", "args": {"radius": wr}},
                    {"name": "extrude", "args": {"distance": -ll1}},
                ]
            },
        )
        # Leg2 — same rotation (integer turns), at end origin (cr, 0, h)
        leg2 = Op(
            "union",
            {
                "ops": [
                    {
                        "name": "transformed",
                        "args": {"offset": [cr, 0, h], "rotate": [rot_x, 0, 0]},
                    },
                    {"name": "circle", "args": {"radius": wr}},
                    {"name": "extrude", "args": {"distance": ll2}},
                ]
            },
        )
        if leg_order_swap:
            ops.extend([leg2, leg1])
        else:
            ops.extend([leg1, leg2])

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
