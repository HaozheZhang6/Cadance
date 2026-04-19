"""Sheet metal tray / chassis — box + shell to simulate folded sheet metal.

Structural type: box → shell (open top) → holes/cutouts.
Mimics Fusion360 sheet metal workflow: flat plate with folded walls.

Easy:   open-top tray (box shell)
Medium: + mounting holes on flanges + edge chamfer
Hard:   + ventilation slots on sides + corner gussets
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class SheetMetalTrayFamily(BaseFamily):
    name = "sheet_metal_tray"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(40, 200)
        width = rng.uniform(30, 150)
        height = rng.uniform(10, 60)
        # Sheet ≥ 2.5 mm at easy so rim/opening reads at montage scale
        # (very thin shell on closed-looking iso view hides the open top).
        t_lo = 2.5 if difficulty == "easy" else 1.5
        sheet_t = rng.uniform(t_lo, max(t_lo + 0.3, min(5.0, height * 0.15)))

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "sheet_thickness": round(sheet_t, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            n_holes = int(rng.choice([2, 4, 6]))
            hole_d = rng.uniform(3.5, max(4.5, min(14, length * 0.08, width * 0.08)))
            params["n_mount_holes"] = n_holes
            params["mount_hole_diameter"] = round(hole_d, 1)
            params["chamfer_length"] = round(
                rng.uniform(0.3, min(1.5, sheet_t * 0.4)), 1
            )

        if difficulty == "hard":
            n_slots = int(rng.choice([2, 3, 4]))
            slot_w = round(rng.uniform(3, max(3.5, min(8, width * 0.08))), 1)
            # total slot span = slot_h + slot_w; keep well within wall height
            max_sh = max(3.0, height * 0.55 - slot_w)
            slot_h_lo = max(2.0, min(height * 0.2, max_sh - 0.5))
            slot_h = round(rng.uniform(slot_h_lo, max_sh), 1)
            params["n_vent_slots"] = n_slots
            params["vent_slot_width"] = slot_w
            params["vent_slot_height"] = slot_h

        return params

    def validate_params(self, params: dict) -> bool:
        L = params["length"]
        W = params["width"]
        H = params["height"]
        t = params["sheet_thickness"]

        if t >= H * 0.3 or H < 8 or L < 25 or W < 20:
            return False
        # Shell requires wall thickness < min dimension
        if t * 2 >= min(L, W, H) * 0.5:
            return False

        hd = params.get("mount_hole_diameter")
        if hd and hd >= min(L, W) * 0.15:
            return False

        sh = params.get("vent_slot_height")
        sw_v = params.get("vent_slot_width", 0)
        if sh and (sh + sw_v) >= H - 3 * t:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        L = params["length"]
        W = params["width"]
        H = params["height"]
        t = params["sheet_thickness"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # Box — chamfer outer top edges BEFORE shell (clean 4-edge selection)
        ops.append(Op("box", {"length": L, "width": W, "height": H}))

        # Chamfer top rim edges (medium+) — BEFORE shell to avoid complex post-shell rim
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Shell open at top → sheet metal tray
        ops.append(Op("faces", {"selector": ">Z"}))
        ops.append(Op("shell", {"thickness": -t}))

        # Mounting holes on bottom face, spread toward corners (medium+)
        n_h = params.get("n_mount_holes")
        hd = params.get("mount_hole_diameter")
        if n_h and hd:
            tags["has_hole"] = True
            half_n = n_h // 2
            # Place holes near corners: inset by hd + t from each edge
            x_inset = round(max(hd / 2 + t + 2, L * 0.12), 3)
            y_margin = round(max(t * 1.5, hd / 2 + t + 1.5), 3)
            y_front = round(-W / 2 + y_margin, 3)
            y_back = round(W / 2 - y_margin, 3)
            if half_n == 1:
                xs = [0.0]
            else:
                x_gap = round((L - 2 * x_inset) / (half_n - 1), 3)
                xs = [round(-L / 2 + x_inset + x_gap * i, 3) for i in range(half_n)]
            hole_pts = []
            for x in xs:
                hole_pts.append((x, y_front))
                hole_pts.append((x, y_back))
            hole_pts = hole_pts[:n_h]
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("pushPoints", {"points": hole_pts}))
            ops.append(Op("hole", {"diameter": hd}))

        # Vent slots on front face (hard)
        n_s = params.get("n_vent_slots")
        sw = params.get("vent_slot_width")
        sh = params.get("vent_slot_height")
        if n_s and sw and sh:
            tags["has_slot"] = True
            spacing = L / (n_s + 1)
            slot_pts = [(round(-L / 2 + spacing * (i + 1), 3), 0.0) for i in range(n_s)]
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("pushPoints", {"points": slot_pts}))
            ops.append(Op("rect", {"length": sw, "width": round(sh + sw, 3)}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
