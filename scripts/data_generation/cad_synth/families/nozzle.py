"""Nozzle — hollow truncated cone (revolve).

Profile: outer frustum wall + inner frustum wall, revolved 360° around Y axis.
Easy:   uniform-wall hollow cone frustum.
Medium: + inlet flange lip.
Hard:   + mounting holes on flange.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class NozzleFamily(BaseFamily):
    name = "nozzle"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        r_in = round(rng.uniform(12, 40), 1)  # inlet (large end) outer radius
        r_out = round(r_in * rng.uniform(0.25, 0.65), 1)  # outlet outer radius
        length = round(rng.uniform(25, 100), 1)
        wall = round(rng.uniform(2, max(2.5, min(r_out * 0.4, 8))), 1)

        # Flange/chamfer/holes now free across all difficulties (was strict by diff)
        flange_prob = {"easy": 0.3, "medium": 0.7, "hard": 0.85}[difficulty]
        chamfer_prob = {"easy": 0.15, "medium": 0.4, "hard": 0.6}[difficulty]
        profile_reverse = bool(rng.random() < 0.5)

        params = {
            "inlet_radius": r_in,
            "outlet_radius": r_out,
            "length": length,
            "wall_thickness": wall,
            "profile_reverse": profile_reverse,
            "difficulty": difficulty,
        }

        if rng.random() < flange_prob:
            params["flange_width"] = round(r_in * rng.uniform(0.2, 0.4), 1)
            params["flange_thickness"] = round(wall * rng.uniform(1.5, 2.5), 1)
            # Mounting holes on flange (50% if flange present)
            if rng.random() < 0.5:
                params["flange_holes_n"] = int(rng.choice([3, 4, 6, 8]))
                params["flange_hole_d"] = round(
                    float(rng.uniform(2.5, max(3.0, params["flange_width"] * 0.3))), 1
                )

        if rng.random() < chamfer_prob:
            params["outlet_chamfer"] = round(min(wall * 0.4, 2.0), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r_in = params["inlet_radius"]
        r_out = params["outlet_radius"]
        wall = params["wall_thickness"]
        L = params["length"]

        if r_out >= r_in:
            return False
        if r_out - wall < 2:
            return False
        if r_in - wall < 3:
            return False
        if wall < 1.5:
            return False
        if L < 15:
            return False

        fw = params.get("flange_width", 0)
        ft = params.get("flange_thickness", 0)
        if fw and ft:
            if ft >= L * 0.3:
                return False

        oc = params.get("outlet_chamfer", 0)
        if oc and oc >= wall * 0.6:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r_in = params["inlet_radius"]
        r_out = params["outlet_radius"]
        L = params["length"]
        wall = params["wall_thickness"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # 2D profile for revolve (in XY plane, revolved around X axis):
        # X = axial position (0 = large/inlet end, L = small/outlet end)
        # Y = radial distance from X axis
        # This orients the nozzle along X so the taper is visible from front view.
        r_in_inner = round(r_in - wall, 4)
        r_out_inner = round(r_out - wall, 4)

        forward_pts = [
            (0.0, round(r_in, 4)),
            (round(L, 4), round(r_out, 4)),
            (round(L, 4), r_out_inner),
            (0.0, r_in_inner),
        ]
        pts = (
            list(reversed(forward_pts))
            if params.get("profile_reverse", False)
            else forward_pts
        )
        ops.append(Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}))
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {
                    "angleDeg": 360,
                    "axisStart": [0, 0, 0],
                    "axisEnd": [1, 0, 0],
                },
            )
        )

        # Flange lip at inlet (medium+): ring added to the large end
        fw = params.get("flange_width")
        ft = params.get("flange_thickness")
        if fw and ft:
            # Flange: annular disk at x=0 (inlet face), extending in -X direction
            # Nozzle axis is along X, so inlet is at X=0, outlet at X=L
            flange_center_x = round(-ft / 2, 4)
            flange_outer_r = round(r_in + fw, 4)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [flange_center_x, 0, 0],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ft, 4),
                                    "radius": flange_outer_r,
                                },
                            },
                        ]
                    },
                )
            )
            # Cut inner bore of flange to keep it as a ring
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [flange_center_x, 0, 0],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ft + 1, 4),
                                    "radius": round(r_in_inner, 4),
                                },
                            },
                        ]
                    },
                )
            )
            # Optional mounting holes around flange (polar pattern)
            n_holes = params.get("flange_holes_n")
            hole_d = params.get("flange_hole_d")
            if n_holes and hole_d:
                tags["has_hole"] = True
                hole_r = round(hole_d / 2, 3)
                bolt_circle_r = round((r_in + flange_outer_r) / 2, 3)
                import math as _m

                for i in range(int(n_holes)):
                    ang = 2 * _m.pi * i / int(n_holes)
                    cy = round(bolt_circle_r * _m.cos(ang), 3)
                    cz = round(bolt_circle_r * _m.sin(ang), 3)
                    ops.append(
                        Op(
                            "cut",
                            {
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [
                                                round(flange_center_x - 0.5, 4),
                                                cy,
                                                cz,
                                            ],
                                            "rotate": [0, 90, 0],
                                        },
                                    },
                                    {
                                        "name": "cylinder",
                                        "args": {
                                            "height": round(ft + 1, 4),
                                            "radius": hole_r,
                                        },
                                    },
                                ]
                            },
                        )
                    )

        # Chamfer outlet edge (hard)
        oc = params.get("outlet_chamfer")
        if oc:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">X"}))
            ops.append(Op("chamfer", {"length": oc}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
