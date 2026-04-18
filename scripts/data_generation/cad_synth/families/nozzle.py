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

        params = {
            "inlet_radius": r_in,
            "outlet_radius": r_out,
            "length": length,
            "wall_thickness": wall,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["flange_width"] = round(r_in * rng.uniform(0.2, 0.4), 1)
            params["flange_thickness"] = round(wall * rng.uniform(1.5, 2.5), 1)

        if difficulty == "hard":
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

        ops.append(Op("moveTo", {"x": 0.0, "y": round(r_in, 4)}))
        ops.append(Op("lineTo", {"x": round(L, 4), "y": round(r_out, 4)}))
        ops.append(Op("lineTo", {"x": round(L, 4), "y": r_out_inner}))
        ops.append(Op("lineTo", {"x": 0.0, "y": r_in_inner}))
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
