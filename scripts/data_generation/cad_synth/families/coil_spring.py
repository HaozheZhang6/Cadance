"""Coil spring — DIN 2095 closed-and-ground compression spring.

Variable-pitch helix: 1 tight closed end-coil (pitch = wire_d) → n active
coils at nominal pitch (≈3·wire_d) → 1 tight closed end-coil → flat grind
planes at z=0 and z=total_height. Profile is a circle swept along the
3-segment helix (a single spline path through computed 3D points).

Construction (matches tmp/manual_family_previews/manual_coil_spring_closed_ground.py):
  1. Build variable-pitch helix point list, start point at (R, 0, 0).
  2. Profile plane = perpendicular to start tangent (rotation about X by
     -atan2(R, pitch_end/(2π))).
  3. Sweep circle(wire_r) along spline(points), Frenet frame.
  4. Cut grind boxes at top + bottom (height 2·grind_t each).

DIN 2095:1973 — preferred wire diameters d (mm).
Spring index c = D/d ∈ [4, 20] (recommended).

Easy:   small wire d 2.0–3.5 mm, fewer turns
Medium: mid range  d 2.5–6.0 mm
Hard:   full range d 2–10 mm

Reference: DIN 2095:1973 Tables 1–2.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_DIN2095_D = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
_SMALL_D = _DIN2095_D[:4]
_MID_D = _DIN2095_D[1:7]
_ALL_D = _DIN2095_D


def _helix_points(R, p_bot, n_bot, p_act, n_act, p_top, n_top, samples_per_turn=24):
    """Variable-pitch helix as 3D points. Single continuous spline path."""

    def _seg(theta0, z0, p, n):
        N = max(4, int(samples_per_turn * n))
        out = []
        for i in range(N + 1):
            f = i / N
            th = theta0 + f * 2 * math.pi * n
            zz = z0 + f * p * n
            out.append((R * math.cos(th), R * math.sin(th), zz))
        return out, theta0 + 2 * math.pi * n, z0 + p * n

    s1, theta0, z = _seg(0.0, 0.0, p_bot, n_bot)
    s2, theta0, z = _seg(theta0, z, p_act, n_act)
    s3, theta0, z = _seg(theta0, z, p_top, n_top)
    return s1 + s2[1:] + s3[1:]


class CoilSpringFamily(BaseFamily):
    name = "coil_spring"
    standard = "DIN 2095"

    def sample_params(self, difficulty: str, rng) -> dict:
        d_pool = (
            _SMALL_D
            if difficulty == "easy"
            else (_MID_D if difficulty == "medium" else _ALL_D)
        )
        wire_d = float(d_pool[int(rng.integers(0, len(d_pool)))])
        wire_r = wire_d / 2
        c = float(rng.choice([4, 5, 6, 8, 10, 12, 16, 20]))
        coil_r = round(c * wire_d / 2, 2)
        n_active = int(rng.choice([3, 4, 5, 6, 7]))
        # n_end coils per side: 1 or 2 (was always 1)
        n_end = int(rng.choice([1, 1, 2]))
        pitch_active = round(wire_d * rng.uniform(2.5, 4.0), 2)
        pitch_end = wire_d
        # Free grind thickness ratio (was fixed 0.4)
        grind_t = round(wire_d * float(rng.uniform(0.25, 0.6)), 3)
        total_h = round(2 * pitch_end * n_end + pitch_active * n_active, 4)
        # Code-syntax: top↔bottom cut order
        cut_order_swap = bool(rng.random() < 0.5)

        return {
            "wire_diameter": wire_d,
            "wire_radius": round(wire_r, 3),
            "spring_index": c,
            "coil_radius": coil_r,
            "mean_coil_diameter": round(coil_r * 2, 3),
            "n_active_coils": float(n_active),
            "n_end_coils": float(n_end),
            "pitch_active": pitch_active,
            "pitch_end": pitch_end,
            "grind_thickness": grind_t,
            "total_height": total_h,
            "cut_order_swap": cut_order_swap,
            "difficulty": difficulty,
            "base_plane": "XY",
        }

    def validate_params(self, params: dict) -> bool:
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        wd = params["wire_diameter"]
        p_act = params["pitch_active"]
        n_act = params["n_active_coils"]
        n_end = params["n_end_coils"]
        if wr < 1.0 or wr >= cr * 0.3:
            return False
        if p_act < wd * 2.2:
            return False
        total_h = 2 * wd * n_end + p_act * n_act
        if total_h < 10 or total_h > 400:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        wd = params["wire_diameter"]
        p_act = params["pitch_active"]
        p_end = params["pitch_end"]
        n_act = int(params["n_active_coils"])
        n_end = int(params["n_end_coils"])
        grind = params["grind_thickness"]

        pts = _helix_points(cr, p_end, n_end, p_act, n_act, p_end, n_end)
        # Round so embedded literals stay short
        pts = [(round(x, 4), round(y, 4), round(z, 4)) for (x, y, z) in pts]
        total_z = pts[-1][2]

        # Profile plane normal = start tangent ≈ (0, R, p_end/(2π))/mag
        h_end = p_end / (2 * math.pi)
        rot_x = round(-math.degrees(math.atan2(cr, h_end)), 4)

        cut_size = round((cr + wr) * 2.5, 3)

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        cut_order_swap = bool(params.get("cut_order_swap", False))
        bottom_cut = Op(
            "cut",
            {
                "ops": [
                    {"name": "transformed", "args": {"offset": [0, 0, -grind]}},
                    {
                        "name": "box",
                        "args": {
                            "length": cut_size,
                            "width": cut_size,
                            "height": 2 * grind,
                        },
                    },
                ]
            },
        )
        top_cut = Op(
            "cut",
            {
                "ops": [
                    {
                        "name": "transformed",
                        "args": {"offset": [0, 0, total_z + grind]},
                    },
                    {
                        "name": "box",
                        "args": {
                            "length": cut_size,
                            "width": cut_size,
                            "height": 2 * grind,
                        },
                    },
                ]
            },
        )
        sweep_op = Op(
            "sweep",
            {
                "path_type": "spline",
                "path_points": pts,
                "path_plane": "XY",
                "isFrenet": True,
            },
        )
        ops = [
            Op("transformed", {"offset": [cr, 0, 0], "rotate": [rot_x, 0, 0]}),
            Op("circle", {"radius": wr}),
            sweep_op,
        ]
        if cut_order_swap:
            ops.extend([top_cut, bottom_cut])
        else:
            ops.extend([bottom_cut, top_cut])

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
