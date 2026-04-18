"""Hinge leaf — flat plate with cylindrical knuckle barrels along one edge.

Shows clearly as a hinge component: flat plate + knuckle barrels + pin bore.

Easy:   leaf plate + 2 knuckle cylinders + pin bore
Medium: + screw holes on leaf face
Hard:   + countersunk screw holes + fillet on leaf edges
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program
from ..pipeline.plane_utils import cylinder_rot_to_lateral2, plane_offset


class HingeFamily(BaseFamily):
    name = "hinge"
    standard = "DIN 7954/7955"

    def sample_params(self, difficulty: str, rng) -> dict:
        leaf_w = rng.uniform(25, 70)
        leaf_h = rng.uniform(40, 120)
        leaf_t = rng.uniform(2, 5)
        knuckle_d = rng.uniform(
            max(6, leaf_t * 2.5),
            max(max(6, leaf_t * 2.5) + 1, min(14, leaf_w * 0.3)),
        )
        pin_d = rng.uniform(2.0, knuckle_d * 0.55)
        n_knuckles = int(rng.choice([2, 3]))
        k_h = round(leaf_h / (n_knuckles + 0.5), 2)

        params = {
            "leaf_width": round(leaf_w, 1),
            "leaf_height": round(leaf_h, 1),
            "leaf_thickness": round(leaf_t, 1),
            "knuckle_diameter": round(knuckle_d, 1),
            "pin_diameter": round(pin_d, 1),
            "n_knuckles": n_knuckles,
            "knuckle_height": k_h,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            n_screws = int(rng.choice([2, 3]))
            screw_d = rng.uniform(2.5, min(5.0, leaf_w * 0.12))
            params["n_screws"] = n_screws
            params["screw_diameter"] = round(screw_d, 1)

        if difficulty == "hard":
            params["csk_diameter"] = round(params["screw_diameter"] * 2.0, 1)
            params["csk_angle"] = 82.0
            params["fillet_radius"] = round(
                rng.uniform(0.5, min(1.5, leaf_t * 0.25)), 1
            )

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
