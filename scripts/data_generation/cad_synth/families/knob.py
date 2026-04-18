"""Knob / handle — tapered frustum sections (DIN 319 control knobs).

DIN 319 Form 1: conical/cylindrical control knobs — standard outer diameter D,
thread designation, and height H series.  All D/H values from DIN 319 Table 1.

Table: (D_mm, thread_M, H_nom)
  D = knob outer diameter [mm]
  M = metric thread for through bore
  H = nominal height [mm]

Easy:   single tapered frustum, small knobs (D 8–20 mm)
Medium: two tapered sections + crown, mid knobs (D 12–40 mm)
Hard:   + knurling grooves + center bore, full range (D 8–80 mm)

Reference: DIN 319:1991 — Control knobs, Form 1 (conical); Table (D, M, H for D 16–80mm)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 319 Table 1 — (D_knob_mm, thread_M_mm, H_nominal_mm)
_DIN319 = [
    (8, 3, 12),
    (10, 4, 14),
    (12, 5, 16),
    (14, 6, 20),
    (16, 6, 22),
    (20, 8, 28),
    (25, 10, 36),
    (32, 10, 45),
    (40, 12, 56),
    (50, 12, 71),
    (63, 16, 90),
    (80, 20, 112),
]
_SMALL = _DIN319[:5]  # D 8–16
_MID = _DIN319[2:9]  # D 12–40
_ALL = _DIN319


class KnobFamily(BaseFamily):
    name = "knob"
    standard = "DIN 319"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        D, M, H = pool[int(rng.integers(0, len(pool)))]
        r_base = round(D / 2, 1)
        r_top = round(r_base * 0.55, 1)  # DIN 319 Form 1: ~55% taper ratio
        h_total = float(H)

        params = {
            "knob_diameter": float(D),
            "thread_m": float(M),
            "base_radius": r_base,
            "top_radius": r_top,
            "total_height": h_total,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # DIN 319 waist taper: mid-section slightly narrowed
            r_waist = round(r_top * 0.75, 1)
            h1 = round(h_total * 0.45, 1)
            h2 = round(h_total * 0.25, 1)
            params["waist_radius"] = r_waist
            params["h_base_to_waist"] = h1
            params["h_waist_to_top"] = h2

        if difficulty == "hard":
            # DIN 319: through bore = thread M, knurling on body
            bore_d = float(M)
            n_knurl = int(rng.choice([12, 16, 20, 24]))
            knurl_d = round(max(0.8, min(2.0, r_base * 0.08)), 1)
            params["bore_diameter"] = bore_d
            params["n_knurl"] = n_knurl
            params["knurl_diameter"] = knurl_d

        return params

    def validate_params(self, params: dict) -> bool:
        rb = params["base_radius"]
        rt = params["top_radius"]
        h = params["total_height"]

        if rt >= rb or h < 8:
            return False

        rw = params.get("waist_radius")
        h1 = params.get("h_base_to_waist")
        h2 = params.get("h_waist_to_top")
        if rw and h1 and h2:
            if h1 + h2 >= h:
                return False
            if rw >= rb:
                return False

        bd = params.get("bore_diameter")
        if bd and bd >= rt * 1.8:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rb = params["base_radius"]
        rt = params["top_radius"]
        h = params["total_height"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        rw = params.get("waist_radius")
        h1 = params.get("h_base_to_waist")
        h2 = params.get("h_waist_to_top")

        if rw and h1 and h2:
            # Medium: two tapered frustum sections + short top cylinder
            # Section 1: base → waist
            t1 = round(math.degrees(math.atan((rb - rw) / h1)), 3)
            ops.append(Op("circle", {"radius": rb}))
            ops.append(Op("extrude", {"distance": round(h1, 3), "taper": t1}))
            # Section 2: waist → crown
            h3 = round(h - h1 - h2, 3)
            t2 = round(math.degrees(math.atan((rw - rt) / h2)), 3)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": round(rw, 3)}))
            ops.append(Op("extrude", {"distance": round(h2, 3), "taper": t2}))
            # Short top cylinder (crown)
            if h3 > 0.5:
                ops.append(Op("workplane", {"selector": ">Z"}))
                ops.append(Op("circle", {"radius": round(rt, 3)}))
                ops.append(Op("extrude", {"distance": h3}))
        else:
            # Easy: single tapered frustum — smooth cone, no loft artifacts
            taper_deg = round(math.degrees(math.atan((rb - rt) / h)), 3)
            ops.append(Op("circle", {"radius": rb}))
            ops.append(Op("extrude", {"distance": round(h, 3), "taper": taper_deg}))

        # Center bore (hard)
        bd = params.get("bore_diameter")
        if bd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        # Knurling grooves: polar array drilled from bottom face (largest radius)
        n_k = params.get("n_knurl")
        kd = params.get("knurl_diameter")
        if n_k and kd:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(
                Op(
                    "polarArray",
                    {
                        "radius": round(rb * 0.88, 3),
                        "startAngle": 0,
                        "angle": 360,
                        "count": n_k,
                    },
                )
            )
            ops.append(Op("hole", {"diameter": kd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
