"""Hollow tube / closed square column — box with rect cutThruAll bore.

Structural type: prismatic extrude (box) + through-bore cutout.
Covers: square tubing, rectangular hollow sections, structural profiles.

Dimensions from EN 10219 SHS/RHS cold-formed hollow sections.

Easy:   square hollow tube (SHS, small)
Medium: + rectangular cross-section (RHS) + chamfer
Hard:   + larger SHS/RHS + mounting holes + end cap slot
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program

# EN 10219 SHS/RHS cold-formed hollow sections — (outer_w, outer_h, wall_t) mm
_EN10219_SHS = [
    (20, 20, 2.0),
    (25, 25, 2.5),
    (30, 30, 2.5),
    (40, 40, 3.0),
    (50, 50, 3.0),
    (60, 60, 3.0),
    (80, 80, 4.0),
    (100, 100, 5.0),
    (120, 120, 5.0),
    (150, 150, 6.0),
]
_EN10219_RHS = [
    (50, 30, 3.0),
    (60, 40, 3.0),
    (80, 40, 3.0),
    (80, 60, 4.0),
    (100, 50, 4.0),
    (100, 60, 4.0),
    (120, 60, 5.0),
    (150, 100, 5.0),
    (200, 100, 6.0),
    (200, 150, 6.0),
]
_SMALL_SHS = _EN10219_SHS[:5]  # 20–50 mm
_MID_ALL = _EN10219_SHS[3:8] + _EN10219_RHS[:6]  # 40–100 mm
_ALL = _EN10219_SHS + _EN10219_RHS


class HollowTubeFamily(BaseFamily):
    name = "hollow_tube"
    standard = "EN 10305"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL_SHS
            if difficulty == "easy"
            else (_MID_ALL if difficulty == "medium" else _ALL)
        )
        outer_w, outer_h, wall_t = pool[int(rng.integers(0, len(pool)))]
        outer_w, outer_h, wall_t = float(outer_w), float(outer_h), float(wall_t)
        length = round(rng.uniform(outer_w * 1.5, outer_w * 5.0), 0)

        params = {
            "outer_width": outer_w,
            "outer_height": outer_h,
            "length": length,
            "wall_thickness": wall_t,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(
                rng.uniform(0.5, max(0.6, wall_t * 0.3)), 1
            )

        if difficulty == "hard":
            n_holes = int(rng.choice([2, 4]))
            hole_d = round(rng.uniform(3, max(3.1, min(8, outer_w * 0.15))), 1)
            params["n_mount_holes"] = n_holes
            params["mount_hole_diameter"] = hole_d
            slot_w = round(rng.uniform(4, max(4.1, min(15, outer_w * 0.3))), 1)
            slot_d = round(rng.uniform(2, max(2.1, wall_t * 1.5)), 1)
            params["end_slot_width"] = slot_w
            params["end_slot_depth"] = slot_d

        return params

    def validate_params(self, params: dict) -> bool:
        ow = params["outer_width"]
        wt = params["wall_thickness"]
        length = params["length"]

        if wt >= ow * 0.35 or wt < 1.5:
            return False
        if length < 20 or length > 1500:
            return False

        oh = params.get("outer_height", ow)
        inner_w = ow - 2 * wt
        inner_h = oh - 2 * wt
        if inner_w < 3 or inner_h < 3:
            return False

        hd = params.get("mount_hole_diameter")
        if hd and hd >= wt * 1.8:
            return False

        sw = params.get("end_slot_width")
        if sw and sw >= ow * 0.7:
            return False
        # slot2D: length must exceed width (wt*0.8) or CadQuery makes a circle, not a slot
        if sw and sw < wt:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ow = params["outer_width"]
        length = params["length"]
        wt = params["wall_thickness"]
        oh = params.get("outer_height", ow)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # Outer box — tube lies along X axis so bore ends face the iso cameras
        ops.append(Op("box", {"length": length, "width": ow, "height": oh}))

        # Inner bore — rect cutThruAll along X axis (from >X face)
        inner_w = round(ow - 2 * wt, 3)
        inner_h = round(oh - 2 * wt, 3)
        ops.append(Op("workplane", {"selector": ">X"}))
        ops.append(Op("rect", {"length": inner_w, "width": inner_h}))
        ops.append(Op("cutThruAll", {}))

        # Chamfer outer long edges (medium+)
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|X"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Mounting holes on >Z face (hard)
        n_mh = params.get("n_mount_holes")
        mhd = params.get("mount_hole_diameter")
        if n_mh and mhd:
            tags["has_hole"] = True
            spacing = round(length / (n_mh + 1), 3)
            mh_pts = [
                (round(-length / 2 + spacing * (i + 1), 3), 0.0) for i in range(n_mh)
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": mh_pts}))
            ops.append(Op("hole", {"diameter": mhd}))

        # End slot on >X face (hard)
        sw = params.get("end_slot_width")
        sd = params.get("end_slot_depth")
        if sw and sd:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": ">X"}))
            ops.append(
                Op("slot2D", {"length": sw, "width": round(wt * 0.8, 2), "angle": 0})
            )
            ops.append(Op("cutBlind", {"depth": sd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
