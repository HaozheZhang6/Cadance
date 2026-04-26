"""Duct elbow — solid rectangular cross-section 90° elbow.

Represents: moulded HVAC duct elbow, thick-wall rectangular pipe bend,
            structural elbow fitting. Solid body with rectangular cross-section
            swept through a 90° arc path.
Distinct from pipe_elbow (round cross-section sweep).

Easy:   solid rectangular elbow sweep.
Medium: + reinforcement rib box on the outer side of the lead section.
Hard:   + flat flange plates at both open ends (union boxes).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class DuctElbowFamily(BaseFamily):
    name = "duct_elbow"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        duct_w = round(rng.uniform(20, 80), 1)  # section width (X dir)
        duct_h = round(rng.uniform(20, 80), 1)  # section height (Y dir)
        bend_r = round(rng.uniform(duct_w * 0.8, duct_w * 2.5), 1)
        lead = round(rng.uniform(10, 50), 1)  # straight run before bend
        trail = round(rng.uniform(10, 50), 1)  # straight run after bend

        wall_t = round(rng.uniform(2, max(3, min(duct_w * 0.1, 8))), 1)
        # Asymmetric wall thickness on x vs y dim (was equal). Independent ratio.
        wall_t_y = round(wall_t * float(rng.uniform(0.7, 1.3)), 1)
        wall_t_y = max(2.0, min(wall_t_y, min(duct_h * 0.4, 10.0)))

        params = {
            "duct_width": duct_w,
            "duct_height": duct_h,
            "bend_radius": bend_r,
            "lead_length": lead,
            "trail_length": trail,
            "wall_thickness": wall_t,
            "wall_thickness_y": wall_t_y,
            "difficulty": difficulty,
        }

        # Rib: medium 80%, easy/hard 30% (was medium only).
        rib_prob = 0.8 if difficulty == "medium" else 0.3
        if rng.random() < rib_prob:
            params["rib_height"] = round(rng.uniform(3, max(4, min(lead * 0.5, 20))), 1)
            params["rib_depth"] = round(
                rng.uniform(3, max(4, min(duct_w * 0.15, 10))), 1
            )

        return params

    def validate_params(self, params: dict) -> bool:
        dw = params["duct_width"]
        dh = params["duct_height"]
        br = params["bend_radius"]
        lead = params["lead_length"]
        trail = params["trail_length"]

        wt = params.get("wall_thickness", 0)
        wty = params.get("wall_thickness_y", wt)
        if wt and (dw - 2 * wt < 5):
            return False
        if wty and (dh - 2 * wty < 5):
            return False

        if dw < 12 or dh < 12:
            return False
        if br < dw * 0.6:
            return False
        if br > dw * 4:
            return False
        if lead < 8 or trail < 8:
            return False

        rh = params.get("rib_height", 0)
        rd = params.get("rib_depth", 0)
        if rh and rh < 3:
            return False
        if rd and rd < 2:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        dw = params["duct_width"]
        dh = params["duct_height"]
        br = params["bend_radius"]
        lead = params["lead_length"]
        trail = params["trail_length"]
        wt = params["wall_thickness"]
        wty = params.get("wall_thickness_y", wt)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Outer solid rectangular sweep through 90° arc.
        ops.append(Op("rect", {"length": round(dw, 4), "width": round(dh, 4)}))
        ops.append(
            Op(
                "sweep",
                {
                    "path_type": "elbow_arc",
                    "lead_length": round(lead, 4),
                    "bend_radius": round(br, 4),
                    "trail_length": round(trail, 4),
                },
            )
        )

        # Hollow bore: cut a smaller elbow sweep along the same path.
        # Asymmetric wall thickness allowed (wt on x, wty on y).
        inner_dw = round(dw - 2 * wt, 4)
        inner_dh = round(dh - 2 * wty, 4)
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "rect",
                            "args": {"length": inner_dw, "width": inner_dh},
                        },
                        {
                            "name": "sweep",
                            "args": {
                                "path_type": "elbow_arc",
                                "lead_length": round(lead, 4),
                                "bend_radius": round(br, 4),
                                "trail_length": round(trail, 4),
                            },
                        },
                    ]
                },
            )
        )

        # Reinforcement rib on outer side of lead section (medium+).
        # A box union on the +X face of the lead run (outer side of bend).
        rh = params.get("rib_height")
        rd = params.get("rib_depth")
        if rh and rd:
            rib_cx = round(dw / 2 + rd / 2, 4)
            rib_cz = round(lead / 2, 4)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [rib_cx, 0.0, rib_cz],
                                    "rotate": [0.0, 0.0, 0.0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(rd, 4),
                                    "width": round(dh * 0.7, 4),
                                    "height": round(rh, 4),
                                },
                            },
                        ]
                    },
                )
            )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
