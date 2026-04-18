"""Hinge leaf — flat plate with cylindrical knuckle barrels (DIN 7954/7955).

DIN 7954: steel butt hinge. Dimensions from Table 1 — (W, H, T, Kd, Pd) mm.
  W = leaf width, H = leaf height, T = leaf thickness,
  Kd = knuckle diameter, Pd = pin diameter.

Easy:   leaf + 2 knuckle cylinders + pin bore (W 20–35)
Medium: + screw holes on leaf face (W 25–60)
Hard:   + countersunk screw holes + fillet (full range)
"""

from ..pipeline.builder import Op, Program
from ..pipeline.plane_utils import cylinder_rot_to_lateral2, plane_offset
from .base import BaseFamily

# DIN 7954 Table 1 — (leaf_W, leaf_H, leaf_T, knuckle_D, pin_D) mm
_DIN7954 = [
    (20, 30, 1.5, 5.0, 2.5),
    (25, 40, 2.0, 6.0, 3.0),
    (30, 50, 2.0, 7.0, 3.5),
    (35, 60, 2.5, 8.0, 4.0),
    (40, 70, 2.5, 9.0, 4.5),
    (50, 80, 3.0, 10.0, 5.0),
    (60, 100, 3.0, 12.0, 6.0),
    (80, 120, 4.0, 14.0, 7.0),
    (100, 150, 5.0, 16.0, 8.0),
]
_SMALL = _DIN7954[:4]  # W 20–35
_MID = _DIN7954[1:7]  # W 25–60
_ALL = _DIN7954


class HingeFamily(BaseFamily):
    name = "hinge"
    standard = "DIN 7954/7955"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        W, H, T, Kd, Pd = pool[int(rng.integers(0, len(pool)))]
        n_knuckles = int(rng.choice([2, 3]))
        k_h = round(H / (n_knuckles + 0.5), 2)

        params = {
            "leaf_size": float(W),
            "leaf_width": float(W),
            "leaf_height": float(H),
            "leaf_thickness": float(T),
            "knuckle_diameter": float(Kd),
            "pin_diameter": float(Pd),
            "n_knuckles": n_knuckles,
            "knuckle_height": k_h,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            n_screws = int(rng.choice([2, 3]))
            screw_d = round(max(2.5, Pd * 0.6), 1)
            params["n_screws"] = n_screws
            params["screw_diameter"] = screw_d

        if difficulty == "hard":
            params["csk_diameter"] = round(params["screw_diameter"] * 2.0, 1)
            params["csk_angle"] = 82.0
            params["fillet_radius"] = round(min(1.5, T * 0.25), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        lw = params["leaf_width"]
        lh = params["leaf_height"]
        lt = params["leaf_thickness"]
        kd = params["knuckle_diameter"]
        pd = params["pin_diameter"]
        kh = params["knuckle_height"]

        if kd >= lw * 0.5 or pd >= kd * 0.7 or lt < 1.5:
            return False
        if kh < 5 or kh > lh:
            return False

        sd = params.get("screw_diameter")
        if sd and sd >= lt * 2:
            return False

        csd = params.get("csk_diameter")
        if csd and csd >= lw * 0.3:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bp = params.get("base_plane", "XY")
        lw = params["leaf_width"]
        lh = params["leaf_height"]
        lt = params["leaf_thickness"]
        kd = params["knuckle_diameter"]
        pd = params["pin_diameter"]
        n = params["n_knuckles"]
        kh = params["knuckle_height"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        kr = round(kd / 2, 3)
        # Knuckle edge: cylinder axis along Y, sitting at x = lw/2 + kr (proud of edge)
        knuckle_x = round(lw / 2 + kr, 3)

        # Leaf plate
        ops.append(Op("box", {"length": lw, "width": lh, "height": lt}))

        # Knuckle Y positions — evenly spaced along leaf height
        gap = round((lh - n * kh) / (n + 1), 3)
        knuckle_ys = [
            round(gap * (i + 1) + kh * i + kh / 2 - lh / 2, 3) for i in range(n)
        ]

        # Knuckle barrels: second-lateral-axis cylinders attached to first-lateral edge.
        # cylinder_rot_to_lateral2 tilts the sub-workplane cylinder to the second lateral.
        knuckle_rot = cylinder_rot_to_lateral2(bp)
        for y in knuckle_ys:
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": plane_offset(bp, knuckle_x, y, 0.0),
                                    "rotate": knuckle_rot,
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(kh, 3),
                                    "radius": kr,
                                },
                            },
                        ]
                    },
                )
            )

        # Pin bore through each knuckle barrel along second lateral axis
        pd_r = round(pd / 2, 3)
        for y in knuckle_ys:
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": plane_offset(bp, knuckle_x, y, 0.0),
                                    "rotate": knuckle_rot,
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(
                                        kh + 2, 3
                                    ),  # +2 to punch fully through
                                    "radius": pd_r,
                                },
                            },
                        ]
                    },
                )
            )

        # Screw holes on leaf face (medium+)
        n_screws = params.get("n_screws")
        sd = params.get("screw_diameter")
        if n_screws and sd:
            screw_spacing = lh / (n_screws + 1)
            screw_pts = [
                [round(-lw / 4, 3), round(-lh / 2 + screw_spacing * (i + 1), 3)]
                for i in range(n_screws)
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": screw_pts}))

            csk_d = params.get("csk_diameter")
            csk_a = params.get("csk_angle")
            if csk_d and csk_a:
                tags["has_chamfer"] = True
                ops.append(
                    Op(
                        "cskHole",
                        {
                            "diameter": sd,
                            "cskDiameter": csk_d,
                            "cskAngle": csk_a,
                        },
                    )
                )
            else:
                ops.append(Op("hole", {"diameter": sd}))

        # Fillet leaf plate edges (hard)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
