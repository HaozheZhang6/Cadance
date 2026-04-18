"""Knob / handle — tapered frustum sections.

Structural type: taper-extrude stacked cylinders (smooth frustum, no loft artifacts).
Covers: control knobs, dial handles, grip bodies.

Easy:   single tapered frustum (base → top)
Medium: two tapered sections (base → waist, waist → crown) + short top cylinder
Hard:   + knurling grooves (polar array of slots) + center bore
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program


class KnobFamily(BaseFamily):
    name = "knob"

    def sample_params(self, difficulty: str, rng) -> dict:
        r_base = rng.uniform(10, 35)
        r_top = rng.uniform(r_base * 0.4, max(r_base * 0.41, r_base * 0.85))
        h_total = rng.uniform(15, 50)

        params = {
            "base_radius": round(r_base, 1),
            "top_radius": round(r_top, 1),
            "total_height": round(h_total, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Waist section for 3-section loft
            r_waist = round(rng.uniform(r_top * 0.6, max(r_top * 0.61, r_top * 0.9)), 1)
            h1 = round(rng.uniform(h_total * 0.35, h_total * 0.55), 1)
            h2 = round(rng.uniform(h_total * 0.15, h_total * 0.3), 1)
            params["waist_radius"] = r_waist
            params["h_base_to_waist"] = h1
            params["h_waist_to_top"] = h2

        if difficulty == "hard":
            bore_d = rng.uniform(4, max(4.1, r_top * 0.6))
            n_knurl = int(rng.choice([12, 16, 20, 24]))
            knurl_d = rng.uniform(1.0, min(3.0, r_base * 0.1))
            params["bore_diameter"] = round(bore_d, 1)
            params["n_knurl"] = n_knurl
            params["knurl_diameter"] = round(knurl_d, 1)

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
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
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
            ops.append(Op("polarArray", {
                "radius": round(rb * 0.88, 3),
                "startAngle": 0, "angle": 360, "count": n_k,
            }))
            ops.append(Op("hole", {"diameter": kd}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
