"""PCB standoff plate — mounting plate with raised standoff pillars for PCB.

Typical use: electronics assembly baseplate, PCB support tray.
Easy:   plate + 4 corner standoffs (cylinders)
Medium: + center standoffs + mounting holes + chamfer
Hard:   + alignment pins + slot cutouts + fillet
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class PcbStandoffPlateFamily(BaseFamily):
    name = "pcb_standoff_plate"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(60, 200)
        width = rng.uniform(40, 150)
        thick = rng.uniform(2, 6)
        # Force inset ≥ 8 so post_od has room (≥ 8mm posts visible at montage scale).
        inset = rng.uniform(8, max(10, min(22, length / 7, width / 7)))
        # Post height ≥ 8mm + diameter ≥ 6mm so posts read as columns, not bumps.
        post_h = rng.uniform(8, 18)
        post_od = rng.uniform(6, max(7, min(12, inset * 0.85)))
        post_bore_d = rng.uniform(2.0, post_od * 0.55)

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "thickness": round(thick, 1),
            "mount_inset": round(inset, 1),
            "post_height": round(post_h, 1),
            "post_outer_diameter": round(post_od, 1),
            "post_bore_diameter": round(post_bore_d, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(rng.uniform(0.3, min(1.0, thick / 4)), 1)
            # Extra mid-edge standoffs
            params["mid_post_count"] = int(rng.choice([2, 4]))
            params["mount_hole_diameter"] = round(
                rng.uniform(2.5, min(5.0, inset * 0.5)), 1
            )

        if difficulty == "hard":
            # Alignment pins (smaller, solid cylinders)
            params["pin_diameter"] = round(rng.uniform(1.5, 3.0), 1)
            params["pin_height"] = round(rng.uniform(2.0, 5.0), 1)
            # Cable routing slot
            slot_l = rng.uniform(20, min(length * 0.4, 80))
            slot_w = rng.uniform(5, 15)
            params["slot_length"] = round(slot_l, 1)
            params["slot_width"] = round(slot_w, 1)
            params["fillet_radius"] = round(rng.uniform(0.3, min(1.0, thick / 4)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w, t = params["length"], params["width"], params["thickness"]
        ins = params["mount_inset"]
        pod = params["post_outer_diameter"]
        pbd = params["post_bore_diameter"]

        if t < 1.5 or ins < 4 or pod < 3:
            return False
        if pbd >= pod * 0.7:
            return False
        if ins + pod / 2 > min(l, w) / 2 - 2:
            return False

        sl = params.get("slot_length")
        sw = params.get("slot_width")
        if sl and sw:
            if sl >= l - 2 * ins or sw >= w / 3:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w, t = params["length"], params["width"], params["thickness"]
        ins = params["mount_inset"]
        post_h = params["post_height"]
        pod = params["post_outer_diameter"]
        pbd = params["post_bore_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "pattern_like": True,
        }

        # Base plate
        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Chamfer (medium+) — BEFORE standoffs: clean 4-edge box top
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Fillet (hard) — BEFORE standoffs: clean 4-edge box bottom; use <Z not |Z
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Collect all standoff positions first (so we extrude all at once from plate top)
        corner_pts = [
            (round(l / 2 - ins, 3), round(w / 2 - ins, 3)),
            (round(l / 2 - ins, 3), round(-w / 2 + ins, 3)),
            (round(-l / 2 + ins, 3), round(w / 2 - ins, 3)),
            (round(-l / 2 + ins, 3), round(-w / 2 + ins, 3)),
        ]
        mid_n = params.get("mid_post_count", 0)
        if mid_n == 2:
            mid_pts = [(0.0, round(w / 2 - ins, 3)), (0.0, round(-w / 2 + ins, 3))]
        elif mid_n == 4:
            mid_pts = [
                (0.0, round(w / 2 - ins, 3)),
                (0.0, round(-w / 2 + ins, 3)),
                (round(l / 2 - ins, 3), 0.0),
                (round(-l / 2 + ins, 3), 0.0),
            ]
        else:
            mid_pts = []

        all_post_pts = corner_pts + mid_pts

        # All standoff posts from plate top in one extrude — avoids floating solids
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": all_post_pts}))
        ops.append(Op("circle", {"radius": pod / 2}))
        ops.append(Op("extrude", {"distance": post_h}))

        # Bore through all standoffs from their tops
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": all_post_pts}))
        ops.append(Op("hole", {"diameter": pbd}))

        # Alignment pins (hard) — transformed union to reliably fuse with plate
        pin_d = params.get("pin_diameter")
        pin_h = params.get("pin_height")
        if pin_d and pin_h:
            # Center pin at plate_top - 0.5 + pin_h/2 → bottom 0.5mm inside plate
            pin_z = round(t / 2 - 0.5 + pin_h / 2, 3)
            for px in [round(l / 4, 3), round(-l / 4, 3)]:
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [px, 0.0, pin_z],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": pin_h,
                                        "radius": round(pin_d / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        # Cable slot (hard)
        sl = params.get("slot_length")
        sw = params.get("slot_width")
        if sl and sw:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("rect", {"length": sl, "width": sw}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
