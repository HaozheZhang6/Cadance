"""Cable routing panel — plate with rows of oval/rectangular cable pass-through slots.

Typical use: server rack cable management, enclosure wiring panels.
Easy:   plate + 1 row of slots + corner holes
Medium: + 2nd row + chamfer
Hard:   + center hole cluster + fillet
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class CableRoutingPanelFamily(BaseFamily):
    name = "cable_routing_panel"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(100, 300)
        width = rng.uniform(60, 180)
        thick = rng.uniform(2, 5)
        inset = rng.uniform(6, max(7, min(20, length / 10, width / 8)))

        n_slots = int(rng.choice([3, 4, 5, 6]))
        slot_l = rng.uniform(20, min(50, length * 0.4))
        slot_w = rng.uniform(6, min(16, width * 0.15))
        # slot spacing (center-to-center along length axis)
        slot_spacing = (length - 2 * inset - slot_l) / max(1, n_slots - 1) if n_slots > 1 else 1
        row_y = rng.uniform(width * 0.15, width * 0.3)

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "thickness": round(thick, 1),
            "mount_inset": round(inset, 1),
            "mount_hole_diameter": round(rng.uniform(3.0, min(6.0, inset * 0.5)), 1),
            "slot_count": n_slots,
            "slot_length": round(slot_l, 1),
            "slot_width": round(slot_w, 1),
            "slot_spacing": round(slot_spacing, 2),
            "row_y_offset": round(row_y, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(rng.uniform(0.3, min(1.2, thick / 3)), 1)
            # Second row at -row_y
            params["has_second_row"] = True

        if difficulty == "hard":
            n_circ = int(rng.choice([3, 4, 5]))
            circ_d_max = max(9.0, min(20, slot_w * 1.2))
            circ_d = rng.uniform(8, circ_d_max)
            params["center_hole_count"] = n_circ
            params["center_hole_diameter"] = round(circ_d, 1)
            params["fillet_radius"] = round(rng.uniform(0.3, min(1.0, thick / 4)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w, t = params["length"], params["width"], params["thickness"]
        ins = params["mount_inset"]
        n = params["slot_count"]
        sl, sw = params["slot_length"], params["slot_width"]
        ss = params["slot_spacing"]
        ry = params["row_y_offset"]

        if t < 1.5 or sl < 8 or sw < 4:
            return False
        # Slots fit along length
        total_span = sl + (n - 1) * ss if n > 1 else sl
        if total_span > l - 2 * ins + 0.5:
            return False
        # Slots fit in width
        if ry + sw / 2 > w / 2 - ins + 0.5:
            return False
        if params.get("has_second_row") and ry + sw / 2 > w / 2 - ins + 0.5:
            return False

        chd = params.get("center_hole_diameter")
        chn = params.get("center_hole_count")
        if chd and chn:
            circ_span = chd * chn + 4 * (chn - 1)
            if circ_span > l * 0.5:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w, t = params["length"], params["width"], params["thickness"]
        ins = params["mount_inset"]
        mhd = params["mount_hole_diameter"]
        n = params["slot_count"]
        sl, sw = params["slot_length"], params["slot_width"]
        ss = params["slot_spacing"]
        ry = params["row_y_offset"]

        ops, tags = [], {
            "has_hole": True, "has_slot": True,
            "has_fillet": False, "has_chamfer": False,
            "pattern_like": True,
        }

        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Chamfer (medium+) and fillet (hard) — BEFORE cuts for clean edge selection
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        def _add_slot_row(y_off):
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": 0.0, "y": round(y_off, 3)}))
            ops.append(Op("rarray", {
                "xSpacing": ss if n > 1 else 1,
                "ySpacing": 1,
                "xCount": n,
                "yCount": 1,
            }))
            ops.append(Op("rect", {"length": sl, "width": sw}))
            ops.append(Op("cutThruAll", {}))

        _add_slot_row(ry)
        if params.get("has_second_row"):
            _add_slot_row(-ry)

        # Center hole cluster (hard)
        chn = params.get("center_hole_count")
        chd = params.get("center_hole_diameter")
        if chn and chd:
            spacing = chd + 4
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("rarray", {
                "xSpacing": spacing, "ySpacing": 1,
                "xCount": chn, "yCount": 1,
            }))
            ops.append(Op("hole", {"diameter": chd}))

        # Corner mounting holes
        ops.append(Op("workplane", {"selector": ">Z"}))
        pts = [
            (round( l/2 - ins, 3), round( w/2 - ins, 3)),
            (round( l/2 - ins, 3), round(-w/2 + ins, 3)),
            (round(-l/2 + ins, 3), round( w/2 - ins, 3)),
            (round(-l/2 + ins, 3), round(-w/2 + ins, 3)),
        ]
        ops.append(Op("pushPoints", {"points": pts}))
        ops.append(Op("hole", {"diameter": mhd}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
