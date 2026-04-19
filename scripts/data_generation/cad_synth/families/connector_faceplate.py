"""Connector faceplate — I/O panel with rectangular cutouts and mounting holes.

Typical use: electronics enclosure front panel, connector access plate.
Easy:   plate + 1 rect cutout + 4 corner holes
Medium: + 2nd cutout + chamfer
Hard:   + slot array + fillet
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class ConnectorFaceplateFamily(BaseFamily):
    name = "connector_faceplate"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(80, 300)
        width = rng.uniform(40, 120)
        thick = rng.uniform(2, 6)
        inset = rng.uniform(6, min(18, length / 8, width / 6))

        # Primary cutout in left half — leaves space on right for secondary.
        max_cw = min(length - 2 * inset - 6, length * 0.40)
        max_ch = min(width - 2 * inset - 6, width * 0.65)
        cut_w = rng.uniform(max(18, max_cw * 0.45), max_cw)
        cut_h = rng.uniform(max(14, max_ch * 0.45), max_ch)
        # Push primary to one side so secondary has room
        cut_x = -rng.uniform(length * 0.12, length * 0.22)

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "thickness": round(thick, 1),
            "mount_inset": round(inset, 1),
            "mount_hole_diameter": round(rng.uniform(3.5, min(7.0, inset * 0.7)), 1),
            "cutout_width": round(cut_w, 1),
            "cutout_height": round(cut_h, 1),
            "cutout_x_offset": round(cut_x, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(rng.uniform(0.3, min(1.2, thick / 3)), 1)
            # Second cutout in right half (primary pushed left). Cap width at
            # space remaining after primary + 8mm gap.
            right_edge = length / 2 - inset
            cut2_x_min = max(0, cut_x + cut_w / 2 + 8)  # right of primary + gap
            cut2_x = rng.uniform(cut2_x_min, max(cut2_x_min + 1, right_edge * 0.5))
            available_w = (right_edge - cut2_x) * 2
            max_c2w = min(length * 0.30, available_w * 0.85)
            max_c2w = max(10, max_c2w)
            cut2_w = rng.uniform(max(10, max_c2w * 0.4), max_c2w)
            max_c2h = min(width - 2 * inset - 6, width * 0.55)
            cut2_h = rng.uniform(max(10, max_c2h * 0.45), max_c2h)
            params["cutout2_width"] = round(cut2_w, 1)
            params["cutout2_height"] = round(cut2_h, 1)
            params["cutout2_x_offset"] = round(cut2_x, 1)

        if difficulty == "hard":
            # Small vent slot array
            n_slots = int(rng.choice([3, 4, 5]))
            slot_l = rng.uniform(5, min(15, width * 0.25))
            slot_w = rng.uniform(1.5, 3.0)
            params["vent_slot_count"] = n_slots
            params["vent_slot_length"] = round(slot_l, 1)
            params["vent_slot_width"] = round(slot_w, 1)
            params["vent_x_offset"] = round(rng.uniform(-length / 6, length / 6), 1)
            params["fillet_radius"] = round(rng.uniform(0.3, min(1.0, thick / 4)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w, t = params["length"], params["width"], params["thickness"]
        ins = params["mount_inset"]
        cw, ch = params["cutout_width"], params["cutout_height"]
        cx = params["cutout_x_offset"]

        if t < 1.5 or ins < 4:
            return False
        # cutout must fit
        if cw >= l - 2 * ins or ch >= w - 2 * ins:
            return False
        if abs(cx) + cw / 2 > l / 2 - ins:
            return False

        c2w = params.get("cutout2_width")
        c2h = params.get("cutout2_height")
        c2x = params.get("cutout2_x_offset", 0)
        if c2w and c2h:
            if c2w >= l - 2 * ins or c2h >= w - 2 * ins:
                return False
            if abs(c2x) + c2w / 2 > l / 2 - ins:
                return False
            # cutouts must not overlap
            if abs(cx - c2x) < (cw + c2w) / 2 + 2:
                return False

        fr = params.get("fillet_radius")
        vsw = params.get("vent_slot_width")
        if fr and vsw and fr >= vsw / 2:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w, t = params["length"], params["width"], params["thickness"]
        ins = params["mount_inset"]
        mhd = params["mount_hole_diameter"]
        cw, ch = params["cutout_width"], params["cutout_height"]
        cx = params["cutout_x_offset"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
        }

        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Chamfer (medium+) — BEFORE cutouts to avoid complex face boundary
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Primary connector cutout
        ops.append(Op("workplane", {"selector": ">Z"}))
        if abs(cx) > 0.1:
            ops.append(Op("center", {"x": round(cx, 3), "y": 0.0}))
        ops.append(Op("rect", {"length": cw, "width": ch}))
        ops.append(Op("cutThruAll", {}))

        # Second cutout (medium+)
        c2w = params.get("cutout2_width")
        c2h = params.get("cutout2_height")
        c2x = params.get("cutout2_x_offset", 0)
        if c2w and c2h:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": round(c2x, 3), "y": 0.0}))
            ops.append(Op("rect", {"length": c2w, "width": c2h}))
            ops.append(Op("cutThruAll", {}))

        # Vent slots (hard)
        nv = params.get("vent_slot_count")
        vsl = params.get("vent_slot_length")
        vsw = params.get("vent_slot_width")
        vx = params.get("vent_x_offset", 0)
        if nv and vsl and vsw:
            spacing = (vsw + 2.5) if nv > 1 else 1
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": round(vx, 3), "y": round(-(w / 4), 3)}))
            ops.append(
                Op(
                    "rarray",
                    {
                        "xSpacing": spacing,
                        "ySpacing": 1,
                        "xCount": nv,
                        "yCount": 1,
                    },
                )
            )
            ops.append(Op("rect", {"length": vsw, "width": vsl}))
            ops.append(Op("cutThruAll", {}))

        # Corner mounting holes
        ops.append(Op("workplane", {"selector": ">Z"}))
        pts = [
            (round(l / 2 - ins, 3), round(w / 2 - ins, 3)),
            (round(l / 2 - ins, 3), round(-w / 2 + ins, 3)),
            (round(-l / 2 + ins, 3), round(w / 2 - ins, 3)),
            (round(-l / 2 + ins, 3), round(-w / 2 + ins, 3)),
        ]
        ops.append(Op("pushPoints", {"points": pts}))
        ops.append(Op("hole", {"diameter": mhd}))

        # Fillet (hard, only when no vent slots — vent slot edges too small for fillet)
        fr = params.get("fillet_radius")
        if fr and not params.get("vent_slot_count"):
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
