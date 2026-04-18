"""Slotted plate — flat plate with rows of long rectangular slots.

Typical use: adjustable mounting rails, cable tray panels, sliding fixtures.
Easy:   plate + 1 row of slots
Medium: + 2nd row + |Z fillet
Hard:   + corner mounting holes + chamfer
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class SlottedPlateFamily(BaseFamily):
    name = "slotted_plate"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(60, 250)
        width  = rng.uniform(40, 150)
        thick  = rng.uniform(4, 15)
        n_slots = int(rng.choice([2, 3, 4, 5]))
        slot_l = rng.uniform(length * 0.3, length * 0.7)
        slot_w_max = max(4.5, min(12, (width - 20) / (n_slots + 1)))
        slot_w = rng.uniform(4, slot_w_max)
        slot_spacing = (width - 10 - slot_w) / max(1, n_slots - 1) if n_slots > 1 else width / 2

        params = {
            "length": round(length, 1), "width": round(width, 1),
            "thickness": round(thick, 1),
            "slot_count": n_slots, "slot_length": round(slot_l, 1),
            "slot_width": round(slot_w, 1),
            "slot_spacing": round(slot_spacing, 2),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["fillet_radius"] = round(rng.uniform(0.5, min(3.0, thick / 3)), 1)
        if difficulty == "hard":
            max_hd = min(5.0, thick * 0.7)
            if max_hd >= 2.0:
                inset = rng.uniform(8, min(20, length / 4, width / 4))
                params["hole_diameter"] = round(rng.uniform(2.0, max_hd), 1)
                params["hole_inset"] = round(inset, 1)
            params["chamfer_length"] = round(rng.uniform(0.3, min(1.5, thick / 4)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w, t = params["length"], params["width"], params["thickness"]
        n = params["slot_count"]
        sl, sw = params["slot_length"], params["slot_width"]
        ss = params["slot_spacing"]

        if t < 3 or sl < 10 or sw < 2:
            return False
        if sl >= l * 0.8:
            return False
        # Slots must fit in width
        if n > 1 and ss * (n - 1) + sw > w - 8 + 0.5:
            return False
        if sw >= w / (n + 0.5):
            return False

        fr = params.get("fillet_radius")
        if fr and fr >= t / 3:
            return False

        hd = params.get("hole_diameter")
        inset = params.get("hole_inset", 0)
        if hd:
            if inset - hd / 2 < 2 or inset + hd / 2 > min(l, w) / 2 - 2:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w, t = params["length"], params["width"], params["thickness"]
        n = params["slot_count"]
        sl, sw = params["slot_length"], params["slot_width"]
        ss = params["slot_spacing"]

        ops, tags = [], {
            "has_slot": True, "has_hole": False,
            "has_fillet": False, "has_chamfer": False, "pattern_like": True,
        }

        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Fillet |Z edges first (before slots break topology)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Row of slots along X, spaced in Y
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rarray", {
            "xSpacing": 1, "ySpacing": ss if n > 1 else 1,
            "xCount": 1, "yCount": n,
        }))
        ops.append(Op("rect", {"length": sl, "width": sw}))
        ops.append(Op("cutThruAll", {}))

        # Corner mounting holes (hard)
        hd = params.get("hole_diameter")
        inset = params.get("hole_inset", 0)
        if hd:
            tags["has_hole"] = True
            pts = [
                (round( l/2 - inset, 3), round( w/2 - inset, 3)),
                (round( l/2 - inset, 3), round(-w/2 + inset, 3)),
                (round(-l/2 + inset, 3), round( w/2 - inset, 3)),
                (round(-l/2 + inset, 3), round(-w/2 + inset, 3)),
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": pts}))
            ops.append(Op("hole", {"diameter": hd}))

        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
