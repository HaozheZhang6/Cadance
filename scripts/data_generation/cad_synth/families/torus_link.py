"""Torus link — solid torus (ring) shape.

Represents: O-ring, gasket, toroidal pressure vessel, decorative ring,
            chain link, lifting ring.

Profile is a circle cross-section revolved 360° around Y axis (XY_ONLY).
Major radius = R (distance from axis to tube centre).
Minor radius = r (tube cross-section radius).

Easy:   plain torus.
Medium: + 4 mounting lugs (flat rectangular pads on outer rim, equally spaced).
Hard:   + through hole in each lug for bolting.
"""

import math  # used for lug angle math below

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class TorusLinkFamily(BaseFamily):
    name = "torus_link"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        R = round(rng.uniform(25, 80), 1)  # major radius
        r = round(rng.uniform(5, min(R * 0.35, 25)), 1)  # minor (tube) radius

        params = {
            "major_radius": R,
            "minor_radius": r,
            "difficulty": difficulty,
        }

        lug_prob = {"easy": 0.2, "medium": 0.7, "hard": 0.85}[difficulty]
        hole_prob = {"easy": 0.0, "medium": 0.4, "hard": 0.85}[difficulty]

        if rng.random() < lug_prob:
            params["lug_width"] = round(rng.uniform(8, max(8.5, min(r * 1.5, 20))), 1)
            params["lug_height"] = round(rng.uniform(6, max(6.5, min(r * 1.2, 16))), 1)
            params["lug_depth"] = round(rng.uniform(4, max(4.5, min(r * 0.8, 12))), 1)
            # Variable lug count (was fixed 4)
            params["n_lugs"] = int(rng.choice([2, 3, 4, 6, 8]))

            if rng.random() < hole_prob:
                params["lug_hole_d"] = round(
                    rng.uniform(3, min(params["lug_width"] * 0.45, 10)), 1
                )

        return params

    def validate_params(self, params: dict) -> bool:
        R = params["major_radius"]
        r = params["minor_radius"]

        if R < 15:
            return False
        if r < 3:
            return False
        if r >= R * 0.45:  # tube must not self-intersect at axis
            return False
        if R - r < 8:  # clearance from axis
            return False

        lw = params.get("lug_width", 0)
        lh = params.get("lug_height", 0)
        ld = params.get("lug_depth", 0)
        if lw and lw < 4:
            return False
        if lh and lh < 3:
            return False
        if ld and ld < 2:
            return False

        hd = params.get("lug_hole_d", 0)
        if hd and lw and hd >= lw * 0.55:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        R = params["major_radius"]
        r = params["minor_radius"]

        # Torus profile: circle of radius r centred at (R, 0) in (x, y) profile plane.
        # Use two semicircular arcs:
        #   right point  = (R+r, 0)
        #   top point    = (R, r)
        #   left point   = (R-r, 0)
        #   bottom point = (R, -r)
        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Torus cross-section: circle of radius r centred at (R, 0) in XY workplane.
        # moveTo shifts the pen so circle() is centred at (R, 0).
        ops.append(Op("moveTo", {"x": R, "y": 0}))
        ops.append(Op("circle", {"radius": r}))
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

        # Mounting lugs at 90° intervals on the outer equator (medium+)
        lw = params.get("lug_width")
        lh = params.get("lug_height")
        ld = params.get("lug_depth")
        n_lugs = int(params.get("n_lugs", 4))
        lug_angles = [round(360.0 * i / n_lugs, 4) for i in range(n_lugs)]
        if lw and lh and ld:
            lug_cx = round(R + r + ld / 2, 4)  # centre of lug in radial direction
            for angle_deg in lug_angles:
                angle_rad = math.radians(angle_deg)
                cx = round(lug_cx * math.cos(angle_rad), 4)
                cz = round(lug_cx * math.sin(angle_rad), 4)
                # Rotate so lug faces radially outward: rotate around Y by angle
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [cx, 0.0, cz],
                                        "rotate": [0.0, -angle_deg, 0.0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(ld, 4),
                                        "width": round(lw, 4),
                                        "height": round(lh, 4),
                                    },
                                },
                            ]
                        },
                    )
                )

        # Through holes in lugs (hard)
        hd = params.get("lug_hole_d")
        if hd and lw and lh and ld:
            tags["has_hole"] = True
            lug_cx = round(R + r + ld / 2, 4)
            for angle_deg in lug_angles:
                angle_rad = math.radians(angle_deg)
                cx = round(lug_cx * math.cos(angle_rad), 4)
                cz = round(lug_cx * math.sin(angle_rad), 4)
                # Drill hole along lug height (Y direction)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [cx, 0.0, cz],
                                        "rotate": [-90.0, 0.0, 0.0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(lh + 1, 4),
                                        "radius": round(hd / 2, 4),
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
