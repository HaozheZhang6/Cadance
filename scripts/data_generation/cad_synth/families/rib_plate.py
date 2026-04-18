"""Ribbed plate — thin baseplate with perpendicular stiffening ribs.

Structural type: thin-walled + rib features.
Ribs run parallel (one direction only), extruded from top face.

Easy:   thin plate + 2-3 parallel ribs
Medium: + mounting corner holes
Hard:   + lightening holes in rib webs + fillet
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class RibPlateFamily(BaseFamily):
    name = "rib_plate"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(60, 200)
        width = rng.uniform(40, 150)
        base_t = rng.uniform(2, 6)        # thin base plate thickness
        rib_h = rng.uniform(8, 35)         # rib height (above base)
        rib_t = rng.uniform(2, min(6, base_t * 2))  # rib thickness
        n_ribs = int(rng.choice([2, 3, 4]))          # ribs along length

        # rib spacing (center-to-center)
        rib_spacing = (length - 2 * rib_t) / max(1, n_ribs - 1) if n_ribs > 1 else length / 2

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "base_thickness": round(base_t, 1),
            "rib_height": round(rib_h, 1),
            "rib_thickness": round(rib_t, 1),
            "rib_count": n_ribs,
            "rib_spacing": round(rib_spacing, 2),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            inset = rng.uniform(6, max(7, min(20, length / 8, width / 8)))
            params["mount_inset"] = round(inset, 1)
            params["mount_hole_diameter"] = round(rng.uniform(3.0, min(6.0, inset * 0.5)), 1)

        if difficulty == "hard":
            # Lightening holes in rib web
            lh_d = rng.uniform(6, max(6.5, min(15, rib_h * 0.5)))
            params["lightening_hole_diameter"] = round(lh_d, 1)
            params["fillet_radius"] = round(rng.uniform(0.5, min(2.0, rib_t / 2)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w = params["length"], params["width"]
        bt = params["base_thickness"]
        rh = params["rib_height"]
        rt = params["rib_thickness"]
        n = params["rib_count"]
        rs = params["rib_spacing"]

        if bt < 1.5 or rh < 5 or rt < 1.5:
            return False
        if n > 1 and rs * (n - 1) + rt > l - rt + 0.5:
            return False

        lhd = params.get("lightening_hole_diameter")
        if lhd and lhd >= rh * 0.65:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w = params["length"], params["width"]
        bt = params["base_thickness"]
        rh = params["rib_height"]
        rt = params["rib_thickness"]
        n = params["rib_count"]
        rs = params["rib_spacing"]

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "thin_wall": True, "has_rib": True,
        }

        # Base plate
        ops.append(Op("box", {"length": l, "width": w, "height": bt}))

        # Longitudinal ribs on top face
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rarray", {
            "xSpacing": rs if n > 1 else 1,
            "ySpacing": 1,
            "xCount": n,
            "yCount": 1,
        }))
        ops.append(Op("rect", {"length": rt, "width": w - 2}))
        ops.append(Op("extrude", {"distance": rh}))

        # Fillet (hard) — BEFORE mounting/lightening holes; <Z = base plate bottom
        # (4 straight edges, no holes yet, avoids |Z which includes rib T-junction edges)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Mounting holes (medium+)
        ins = params.get("mount_inset")
        mhd = params.get("mount_hole_diameter")
        if ins and mhd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            pts = [
                (round( l/2 - ins, 3), round( w/2 - ins, 3)),
                (round( l/2 - ins, 3), round(-w/2 + ins, 3)),
                (round(-l/2 + ins, 3), round( w/2 - ins, 3)),
                (round(-l/2 + ins, 3), round(-w/2 + ins, 3)),
            ]
            ops.append(Op("pushPoints", {"points": pts}))
            ops.append(Op("hole", {"diameter": mhd}))

        # Lightening holes in rib web (hard) — drilled from front face through each rib
        lhd = params.get("lightening_hole_diameter")
        if lhd:
            tags["has_hole"] = True
            # Compute rib X positions from rarray params (same as rib extrude above)
            if n > 1:
                rib_xs = [round(-(n - 1) / 2 * rs + i * rs, 3) for i in range(n)]
            else:
                rib_xs = [0.0]
            lh_pts = [(x, round(bt / 2 + rh / 2, 3)) for x in rib_xs]
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("pushPoints", {"points": lh_pts}))
            ops.append(Op("hole", {"diameter": lhd}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
