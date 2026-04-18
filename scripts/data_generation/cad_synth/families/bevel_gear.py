"""Bevel gear — tapered gear body derived from two gear profiles.

variant=straight_bevel: standard straight bevel gear
variant=miter:          1:1 bevel gear with 45-degree pitch angle

Easy:   tapered gear body + bore
Medium: + bearing-seat recess
Hard:   + small bore keyway
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily, din6885a_keyway


def _gear_pts_from_pitch(
    pitch_r: float, module: float, n_teeth: int, pa_deg: float = 20.0, n_inv: int = 4
) -> list[tuple[float, float]]:
    pa = math.radians(pa_deg)
    r_p = pitch_r
    r_b = r_p * math.cos(pa)
    r_a = r_p + module
    r_d = max(r_b * 0.98, r_p - 1.1 * module)
    inv_pa = math.tan(pa) - pa
    t_tip = math.sqrt(max(1e-9, (r_a / r_b) ** 2 - 1))
    t_root = math.sqrt(max(0.0, (r_d / r_b) ** 2 - 1))

    def inv_xy(t, phi0, mirror=False):
        x = r_b * (math.cos(t) + t * math.sin(t))
        y = r_b * (math.sin(t) - t * math.cos(t))
        if mirror:
            y = -y
        c, s = math.cos(phi0), math.sin(phi0)
        return x * c - y * s, x * s + y * c

    pts = []
    for i in range(n_teeth):
        tc = 2 * math.pi * i / n_teeth
        phi_r = tc - math.pi / (2 * n_teeth) - inv_pa
        phi_l = tc + math.pi / (2 * n_teeth) + inv_pa
        gap = tc - math.pi / n_teeth
        pts.append((round(r_d * math.cos(gap), 3), round(r_d * math.sin(gap), 3)))
        for j in range(n_inv + 1):
            t = t_root + (t_tip - t_root) * j / n_inv
            px, py = inv_xy(t, phi_r, mirror=False)
            pts.append((round(px, 3), round(py, 3)))
        pts.append((round(r_a * math.cos(tc), 3), round(r_a * math.sin(tc), 3)))
        for j in range(n_inv + 1):
            t = t_tip - (t_tip - t_root) * j / n_inv
            px, py = inv_xy(t, phi_l, mirror=True)
            pts.append((round(px, 3), round(py, 3)))
    return pts


class BevelGearFamily(BaseFamily):
    name = "bevel_gear"
    standard = "ISO 23509"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(["straight_bevel", "miter"])
        _ISO54 = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5, 1.125, 1.375, 1.75, 2.25, 2.75]
        m = float(rng.choice(_ISO54))
        z = int(rng.integers(12, 32))
        r_p = m * z / 2
        pitch_angle = 45.0 if variant == "miter" else round(rng.uniform(20, 45), 1)
        face_w = round(rng.uniform(m * 4, min(m * 8, r_p * 0.72)), 1)
        bore_d = round(rng.uniform(r_p * 0.2, max(r_p * 0.21, r_p * 0.45)), 1)
        cone_h = round(r_p / math.tan(math.radians(pitch_angle)), 1)
        small_r = round(max(1.0, r_p - face_w * math.sin(math.radians(pitch_angle))), 2)

        params = {
            "variant": variant,
            "module": m,
            "n_teeth": z,
            "pitch_radius": round(r_p, 2),
            "pitch_angle": pitch_angle,
            "face_width": face_w,
            "cone_height": cone_h,
            "small_radius": small_r,
            "bore_diameter": bore_d,
            "difficulty": difficulty,
        }

        if difficulty == "medium":
            kw, kd = din6885a_keyway(bore_d)
            params["keyway_width"] = kw
            params["keyway_depth"] = kd
            seat_d = round(
                rng.uniform(
                    bore_d * 1.45, max(bore_d * 1.5, min(r_p * 0.65, bore_d * 2.2))
                ),
                1,
            )
            seat_depth = round(
                rng.uniform(0.8, max(0.9, params["face_width"] * 0.16)), 1
            )
            params["bearing_seat_diameter"] = seat_d
            params["bearing_seat_depth"] = seat_depth
        elif difficulty == "hard":
            kw, kd = din6885a_keyway(bore_d)
            params["keyway_width"] = kw
            params["keyway_depth"] = kd

        return params

    def validate_params(self, params: dict) -> bool:
        rp = params["pitch_radius"]
        bd = params["bore_diameter"]
        sr = params["small_radius"]
        fw = params["face_width"]
        ch = params["cone_height"]

        if bd >= rp * 0.55 or sr < 1.5:
            return False
        if fw >= rp or ch < 3:
            return False

        kw = params.get("keyway_width")
        if kw and kw >= bd * 0.5:
            return False
        seat_d = params.get("bearing_seat_diameter")
        seat_depth = params.get("bearing_seat_depth")
        if seat_d is not None:
            if seat_d <= bd * 1.2 or seat_d >= rp * 1.6:
                return False
        if seat_depth is not None and seat_depth >= ch * 0.3:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        m = params["module"]
        z = params["n_teeth"]
        rp = params["pitch_radius"]
        ch = params["cone_height"]
        sr = params["small_radius"]
        bd = params["bore_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        top_pitch_r = round(max(bd / 2 + 1.2, sr - m * 0.2), 3)
        top_module = round(max(m * 0.42, m * (top_pitch_r / rp) * 0.9), 3)
        base_pts = _gear_pts_from_pitch(rp, m, z, pa_deg=20.0, n_inv=4)
        top_pts = _gear_pts_from_pitch(top_pitch_r, top_module, z, pa_deg=20.0, n_inv=4)

        ops.append(Op("polyline", {"points": base_pts}))
        ops.append(Op("close", {}))
        ops.append(Op("workplane_offset", {"offset": ch}))
        ops.append(Op("polyline", {"points": top_pts}))
        ops.append(Op("close", {}))
        ops.append(Op("loft", {"combine": True}))

        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": bd}))

        seat_d = params.get("bearing_seat_diameter")
        seat_depth = params.get("bearing_seat_depth")
        if seat_d and seat_depth:
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("circle", {"radius": round(seat_d / 2, 3)}))
            ops.append(Op("cutBlind", {"depth": seat_depth}))

        kw = params.get("keyway_width")
        kd = params.get("keyway_depth")
        if kw and kd:
            tags["has_slot"] = True
            bore_r = bd / 2
            rect_height = round(bore_r + kd, 3)
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(
                Op(
                    "center",
                    {
                        "x": 0.0,
                        "y": round(rect_height / 2, 3),
                    },
                )
            )
            ops.append(Op("rect", {"length": round(kw, 3), "width": rect_height}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
