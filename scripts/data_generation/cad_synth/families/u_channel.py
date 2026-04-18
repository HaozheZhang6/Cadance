"""U-channel (C-channel) — UPN series structural profile (EN 10279).

Geometry: box with inner channel cut blind from the open face,
leaving a web at the bottom and two side arms (flanges).

UPN dimensions are exact nominal values from EN 10279 Table 1.
Length (cut-to-length dimension) sampled in range [4h, 12h].

Table: (designation, h_height, b_flange, tw_web, tf_flange) — all mm.
Simplified geometry: wall_thickness = tf (flange), web modelled as equal
thickness (acceptable approximation for data synthesis).

Easy:   UPN30–UPN100 (small sizes); plain U profile.
Medium: UPN80–UPN200; + fillet on inner bottom corners + chamfer on arm tips.
Hard:   full range UPN30–UPN300; + mounting holes on the web.

Reference: EN 10279:2000 — Hot-rolled steel channels; Table (UPN 30–UPN 400, h, b, tw, tf)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# UPN series — EN 10279 exact nominal values (mm)
# (designation, h, b, tw, tf)
_UPN = [
    ("UPN30", 30, 33, 5.0, 7.0),
    ("UPN40", 40, 35, 5.0, 7.0),
    ("UPN50", 50, 38, 5.0, 7.0),
    ("UPN65", 65, 42, 5.5, 7.5),
    ("UPN80", 80, 45, 6.0, 8.0),
    ("UPN100", 100, 50, 6.0, 8.5),
    ("UPN120", 120, 55, 7.0, 9.0),
    ("UPN140", 140, 60, 7.0, 10.0),
    ("UPN160", 160, 65, 7.5, 10.5),
    ("UPN180", 180, 70, 8.0, 11.0),
    ("UPN200", 200, 75, 8.5, 11.5),
    ("UPN220", 220, 80, 9.0, 12.5),
    ("UPN240", 240, 85, 9.5, 13.0),
    ("UPN260", 260, 90, 10.0, 14.0),
    ("UPN280", 280, 95, 10.0, 15.0),
    ("UPN300", 300, 100, 10.0, 16.0),
]

_SMALL = [r for r in _UPN if r[1] <= 100]  # UPN30–UPN100
_MEDIUM = [r for r in _UPN if 80 <= r[1] <= 200]  # UPN80–UPN200
_ALL = _UPN


class UChannelFamily(BaseFamily):
    """Parametric U-channel — UPN series, box-minus-cutout geometry."""

    name = "u_channel"
    standard = "EN 10279"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _SMALL
        elif difficulty == "medium":
            pool = _MEDIUM
        else:
            pool = _ALL

        desig, h, b, tw, tf = pool[int(rng.integers(0, len(pool)))]

        # Cut-to-length: 4h–12h, snapped to 25 mm
        raw_l = rng.uniform(h * 4, h * 12)
        length = round(raw_l / 25) * 25
        length = max(length, 60)

        # Use tf (flange thickness) as the unified wall thickness for box-cut geometry
        wall_t = float(tf)

        params = {
            "designation": desig,
            "outer_width": float(b),
            "arm_height": float(h),
            "length": float(length),
            "wall_thickness": wall_t,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_fr = min(wall_t * 0.35, 3.0)
            if max_fr >= 0.5:
                params["fillet_radius"] = round(rng.uniform(0.5, max_fr), 1)
            max_cl = min(wall_t * 0.25, 2.0)
            if max_cl >= 0.3:
                params["chamfer_length"] = round(rng.uniform(0.3, max_cl), 1)

        if difficulty == "hard":
            inner_w = b - 2 * wall_t
            max_hd = min(wall_t * 0.6, 5.0, inner_w / 3)
            if max_hd >= 2.0:
                hd = round(rng.uniform(2.0, max_hd), 1)
                n_holes = int(rng.choice([2, 3, 4]))
                spacing = (
                    round((length - 20) / max(1, n_holes - 1), 1)
                    if n_holes > 1
                    else length
                )
                params["hole_diameter"] = hd
                params["hole_count"] = n_holes
                params["hole_spacing"] = spacing

        return params

    def validate_params(self, params: dict) -> bool:
        ow = params["outer_width"]
        ah = params["arm_height"]
        ln = params["length"]
        wt = params["wall_thickness"]

        if wt < 1.5:
            return False
        if ow - 2 * wt < 3:
            return False
        if ah - wt < 3:
            return False
        if ln < 20:
            return False

        fr = params.get("fillet_radius")
        if fr is not None and fr >= wt * 0.45:
            return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= wt * 0.35:
            return False

        hd = params.get("hole_diameter")
        if hd is not None:
            inner_w = ow - 2 * wt
            if hd >= inner_w / 2 or hd >= wt:
                return False
            n = params.get("hole_count", 1)
            sp = params.get("hole_spacing", 0)
            if n > 1 and sp * (n - 1) > ln - 10:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ow = params["outer_width"]
        ah = params["arm_height"]
        ln = params["length"]
        wt = params["wall_thickness"]

        inner_w = ow - 2 * wt
        inner_h = ah - wt

        ops = []
        tags = {
            "has_hole": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        ops.append(Op("box", {"length": ow, "width": ln, "height": ah}))

        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rect", {"length": inner_w, "width": ln}))
        ops.append(Op("cutBlind", {"depth": inner_h}))

        fr = params.get("fillet_radius")
        if fr is not None:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Y"}))
            ops.append(Op("fillet", {"radius": fr}))

        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        hd = params.get("hole_diameter")
        n_holes = params.get("hole_count", 0)
        sp = params.get("hole_spacing", 1)
        if hd and n_holes:
            tags["has_hole"] = True
            pts = []
            for i in range(n_holes):
                y = (i - (n_holes - 1) / 2) * sp
                pts.append((0.0, round(y, 3)))
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("pushPoints", {"points": pts}))
            ops.append(Op("hole", {"diameter": hd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
