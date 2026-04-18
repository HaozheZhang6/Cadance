"""Dome cap — cylindrical base with hemispherical top.

Common in pressure vessel end caps, lamp housings, sensor covers.

Easy:   solid dome cap (cylinder + hemisphere via revolve).
Medium: + hollow bore from bottom (leaves thin shell).
Hard:   + bolt hole pattern on bottom flange face.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class DomeCapFamily(BaseFamily):
    name = "dome_cap"

    def sample_params(self, difficulty: str, rng) -> dict:
        r = round(rng.uniform(20, 70), 1)
        h_cyl = round(rng.uniform(15, 50), 1)
        wall = round(rng.uniform(3, min(r * 0.2, 10)), 1)

        params = {
            "radius": r,
            "cyl_height": h_cyl,
            "wall": wall,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_bd = h_cyl * 0.75
            params["bore_depth"] = round(rng.uniform(h_cyl * 0.3, max_bd), 1)

        if difficulty == "hard":
            params["n_holes"] = int(rng.choice([4, 6, 8]))
            params["hole_diameter"] = round(rng.uniform(3, max(3.5, min(r * 0.12, 8))), 1)
            params["hole_pcd"] = round(r * rng.uniform(0.65, 0.82), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r = params["radius"]
        h_cyl = params["cyl_height"]
        wall = params["wall"]

        if r < 15:
            return False
        if h_cyl < 10:
            return False
        if wall < 2 or wall >= r * 0.4:
            return False

        bd = params.get("bore_depth", 0)
        if bd and (bd >= h_cyl or bd < 3):
            return False

        hd = params.get("hole_diameter", 0)
        pcd = params.get("hole_pcd", 0)
        if hd and pcd and (pcd + hd / 2 >= r or pcd - hd / 2 <= wall + 2):
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r = params["radius"]
        h_cyl = params["cyl_height"]
        wall = params["wall"]

        # Quarter-circle arc midpoint: center=(0, h_cyl), start=(r, h_cyl), end=(0, h_cyl+r)
        # Point at 45° from center: (r*cos45, h_cyl + r*sin45)
        s2 = math.sqrt(2) / 2
        mid_x = round(r * s2, 4)
        mid_y = round(h_cyl + r * s2, 4)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # 2-D profile revolved around Y axis [0,1,0].  x = radial, y = axial.
        ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
        ops.append(Op("lineTo", {"x": round(r, 4), "y": 0.0}))
        ops.append(Op("lineTo", {"x": round(r, 4), "y": round(h_cyl, 4)}))
        ops.append(
            Op(
                "threePointArc",
                {
                    "point1": [mid_x, mid_y],
                    "point2": [0.0, round(h_cyl + r, 4)],
                },
            )
        )
        ops.append(Op("close", {}))
        # CadQuery revolve axis is in workplane-local coordinates.
        # [0,1,0] = v-axis of the current workplane, which is the profile's
        # height direction for all three base planes (XY→Y, XZ→Z, YZ→Z).
        ops.append(
            Op(
                "revolve",
                {
                    "angleDeg": 360,
                    "axisStart": [0, 0, 0],
                    "axisEnd": [0, 1, 0],
                },
            )
        )

        # Hollow bore from bottom (medium+)
        bd = params.get("bore_depth")
        if bd:
            bore_r = round(r - wall, 4)
            ops.append(Op("workplane", {"selector": "<Y"}))
            ops.append(Op("circle", {"radius": bore_r}))
            ops.append(Op("cutBlind", {"depth": round(bd, 4)}))

        # Bolt holes on bottom face (hard)
        n = params.get("n_holes")
        hd = params.get("hole_diameter")
        pcd = params.get("hole_pcd")
        if n and hd and pcd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": "<Y"}))
            ops.append(
                Op(
                    "polarArray",
                    {
                        "radius": round(pcd, 4),
                        "startAngle": 0,
                        "angle": 360,
                        "count": n,
                    },
                )
            )
            ops.append(Op("hole", {"diameter": round(hd, 4)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
