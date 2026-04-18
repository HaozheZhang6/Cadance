"""Capsule — cylinder with two hemispherical end caps.

Represents: pill/capsule container, pressure vessel, fluid reservoir.

Profile is revolved 360° around Y axis (XY_ONLY).
x = radial distance (≥0), y = height (0=bottom apex, H=top apex).

Easy:   solid capsule body.
Medium: + equatorial weld ring (annular band at mid-height, union).
Hard:   + two end port stubs (short cylinders at top and bottom apices).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class CapsuleFamily(BaseFamily):
    name = "capsule"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        r = round(rng.uniform(15, 60), 1)
        h_cyl = round(rng.uniform(20, 100), 1)

        params = {
            "radius": r,
            "cyl_height": h_cyl,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["ring_width"] = round(rng.uniform(3, max(3.5, min(r * 0.2, 10))), 1)
            params["ring_height"] = round(rng.uniform(4, max(4.5, min(r * 0.15, 8))), 1)

        if difficulty == "hard":
            params["stub_radius"] = round(
                rng.uniform(4, max(4.5, min(r * 0.35, 20))), 1
            )
            params["stub_height"] = round(rng.uniform(8, max(8.5, min(r * 0.6, 25))), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r = params["radius"]
        h_cyl = params["cyl_height"]

        if r < 10:
            return False
        if h_cyl < 15:
            return False

        rw = params.get("ring_width", 0)
        rh = params.get("ring_height", 0)
        if rw and rw >= r * 0.35:
            return False
        if rh and rh < 2:
            return False

        sr = params.get("stub_radius", 0)
        sh = params.get("stub_height", 0)
        if sr and sr >= r * 0.55:
            return False
        if sh and sh < 5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r = params["radius"]
        h_cyl = params["cyl_height"]
        H = round(h_cyl + 2 * r, 4)  # total height

        s2 = math.sqrt(2) / 2  # sin/cos 45°

        # Bottom hemisphere arc: from (0,0) to (r, r)
        # Circle center at (0, r); midpoint at 45° = (r*s2, r - r*s2) = (r*s2, r*(1-s2))
        bot_mid_x = round(r * s2, 4)
        bot_mid_y = round(r * (1.0 - s2), 4)

        # Top hemisphere arc: from (r, r+h_cyl) to (0, H)
        # Circle center at (0, r+h_cyl); midpoint at 45° = (r*s2, r+h_cyl + r*s2)
        top_start_y = round(r + h_cyl, 4)
        top_mid_x = round(r * s2, 4)
        top_mid_y = round(r + h_cyl + r * s2, 4)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Profile: bottom apex → bottom arc → cylinder wall → top arc → close
        ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
        ops.append(
            Op(
                "threePointArc",
                {
                    "point1": [bot_mid_x, bot_mid_y],
                    "point2": [round(r, 4), round(r, 4)],
                },
            )
        )
        ops.append(Op("lineTo", {"x": round(r, 4), "y": top_start_y}))
        ops.append(
            Op(
                "threePointArc",
                {
                    "point1": [top_mid_x, top_mid_y],
                    "point2": [0.0, H],
                },
            )
        )
        ops.append(Op("close", {}))
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

        # Weld ring at equator (medium+): thin annular band
        rw = params.get("ring_width")
        rh = params.get("ring_height")
        if rw and rh:
            equator_y = round(H / 2, 4)
            ring_r = round(r + rw, 4)
            # Union a wide cylinder at equator, then cut inner bore so it's a ring
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, equator_y, 0.0],
                                    "rotate": [-90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": round(rh, 4), "radius": ring_r},
                            },
                        ]
                    },
                )
            )
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, equator_y, 0.0],
                                    "rotate": [-90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(rh + 1, 4),
                                    "radius": round(r, 4),
                                },
                            },
                        ]
                    },
                )
            )

        # End port stubs (hard): short cylinders at top and bottom apices
        sr = params.get("stub_radius")
        sh = params.get("stub_height")
        if sr and sh:
            tags["has_hole"] = False  # stubs are solid protrusions
            # Bottom stub: points in -Y from y=0
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, -round(sh / 2, 4), 0.0],
                                    "rotate": [90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(sh, 4),
                                    "radius": round(sr, 4),
                                },
                            },
                        ]
                    },
                )
            )
            # Top stub: points in +Y from y=H
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, round(H + sh / 2, 4), 0.0],
                                    "rotate": [-90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(sh, 4),
                                    "radius": round(sr, 4),
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
