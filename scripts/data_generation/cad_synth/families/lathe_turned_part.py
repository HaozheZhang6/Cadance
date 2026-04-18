"""Lathe-turned part — complex revolved profile with multiple diameters/features.

Structural type: revolution solid with stepped OD, grooves, taper.
Completely different topology from any box-based family.

Easy:   2-step OD via revolve (large + small diameter)
Medium: + neck groove + taper transition
Hard:   + bore + undercut relief groove
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class LatheTurnedPartFamily(BaseFamily):
    name = "lathe_turned_part"

    def sample_params(self, difficulty: str, rng) -> dict:
        # Main body: large-diameter section
        d1 = rng.uniform(20, 80)    # large OD
        h1 = rng.uniform(10, 40)    # length of large section
        d2 = rng.uniform(d1 * 0.4, d1 * 0.75)   # small-end OD
        h2 = rng.uniform(10, 35)    # length of small section

        params = {
            "d1": round(d1, 1),
            "h1": round(h1, 1),
            "d2": round(d2, 1),
            "h2": round(h2, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Neck groove between sections
            gw = rng.uniform(2.0, max(2.1, min(6.0, d2 * 0.15)))
            gd = rng.uniform(1.0, max(1.1, min(4.0, d2 * 0.12)))
            params["groove_width"] = round(gw, 1)
            params["groove_depth"] = round(gd, 1)
            # Taper section (frustum) between d1 and d2
            params["has_taper"] = True
            params["taper_length"] = round(rng.uniform(3, min(15, h1 * 0.4)), 1)
            params["chamfer_length"] = round(rng.uniform(0.5, max(0.6, min(2.0, d2 * 0.05))), 1)

        if difficulty == "hard":
            # Center bore through entire part
            bore_d = rng.uniform(d2 * 0.25, d2 * 0.55)
            params["bore_diameter"] = round(bore_d, 1)
            # Undercut relief groove near shoulder
            params["undercut_width"] = round(rng.uniform(1.5, min(5.0, gw * 1.5)), 1)
            params["undercut_depth"] = round(rng.uniform(0.5, min(2.5, gd)), 1)
            params["fillet_radius"] = round(rng.uniform(0.5, max(0.6, min(2.0, d2 * 0.06))), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        d1, h1 = params["d1"], params["h1"]
        d2, h2 = params["d2"], params["h2"]

        if d2 >= d1 or d2 < 6 or h1 < 5 or h2 < 5:
            return False

        gw = params.get("groove_width")
        gd = params.get("groove_depth")
        if gw and gd:
            if gd >= d2 / 2 - 2:
                return False

        bd = params.get("bore_diameter")
        if bd:
            if bd >= d2 - 2 * params.get("groove_depth", 0) - 3:
                return False

        tl = params.get("taper_length")
        if tl and tl >= h1:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1, h1 = params["d1"], params["h1"]
        d2, h2 = params["d2"], params["h2"]

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": True, "multi_stage": True,
        }

        # Build a polyline cross-section profile then revolve around Y axis.
        # Profile x=radius, y=axial position (y=0 at bottom, increasing upward).
        # Points (right side, bottom to top):
        r1 = round(d1 / 2, 3)
        r2 = round(d2 / 2, 3)
        gw = params.get("groove_width", 0)
        gd = params.get("groove_depth", 0)
        tl = params.get("taper_length", 0)
        has_taper = params.get("has_taper", False)

        # Y positions
        y0 = 0.0
        y1 = round(h1, 3)  # top of large section

        TRANS = 2.0  # angled step transition length (mm) — per reference

        if has_taper and tl:
            # explicit taper: large → small over taper_length (no extra TRANS step)
            y_shoulder = round(y1 + tl, 3)   # where r2 is first reached
            y_top = round(y_shoulder + h2, 3)
        else:
            # 2mm angled transition: r1→y1, then diagonal to r2 at y1+TRANS
            y_shoulder = round(y1 + TRANS, 3)
            y_top = round(y_shoulder + h2, 3)

        # Groove position: centred at shoulder where r2 begins
        if gw and gd:
            gy_start = round(y_shoulder - gw / 2, 3)
            gy_end   = round(y_shoulder + gw / 2, 3)
            r_groove = round(r2 - gd, 3)

        # Build profile via lineTo then revolve
        ops.append(Op("moveTo", {"x": 0.0, "y": y0}))
        ops.append(Op("lineTo", {"x": r1,  "y": y0}))          # bottom face
        ops.append(Op("lineTo", {"x": r1,  "y": y1}))          # outer large wall
        # Transition: taper (medium+) or 2mm diagonal step (easy) → r2 at y_shoulder
        ops.append(Op("lineTo", {"x": r2, "y": y_shoulder}))

        if gw and gd:
            # groove at shoulder
            ops.append(Op("lineTo", {"x": r2,      "y": gy_start}))
            ops.append(Op("lineTo", {"x": r_groove, "y": gy_start}))
            ops.append(Op("lineTo", {"x": r_groove, "y": gy_end}))
            ops.append(Op("lineTo", {"x": r2,       "y": gy_end}))
            ops.append(Op("lineTo", {"x": r2, "y": y_top}))    # small OD wall
            tags["has_slot"] = True
        else:
            ops.append(Op("lineTo", {"x": r2, "y": y_top}))    # small OD wall

        ops.append(Op("lineTo", {"x": 0.0, "y": y_top}))       # top face (to axis)
        ops.append(Op("close", {}))
        ops.append(Op("revolve", {
            "angleDeg": 360,
            "axisStart": [0, 0, 0],
            "axisEnd": [0, 1, 0],
        }))

        # Chamfer top edge (medium+) — before bore to avoid multi-circle selection
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Y"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Fillet bottom edge (hard) — before bore to avoid multi-circle selection
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Y"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Bore (hard)
        bd = params.get("bore_diameter")
        if bd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": "<Y"}))
            ops.append(Op("hole", {"diameter": bd}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
