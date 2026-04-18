"""L-bracket family — two perpendicular arms joined at right angle.

Geometry: bounding box minus inner corner cutout, giving an L-shaped profile
extruded to the bracket depth.  All ops are standard CadQuery box/workplane/rect/
cutThruAll — no polyline needed.
"""

import math

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class LBracketFamily(BaseFamily):
    """Parametric L-bracket: two perpendicular arms, uniform thickness."""

    name = "l_bracket"
    standard = "EN 10056"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for an L-bracket at given difficulty."""
        arm1 = rng.uniform(20, 150)  # free length of horizontal arm
        arm2 = rng.uniform(20, 150)  # free height of vertical arm
        thick = rng.uniform(3, 15)
        depth = rng.uniform(10, 60)  # bracket depth (perpendicular to L profile)

        params = {
            "arm1_length": round(arm1, 1),
            "arm2_height": round(arm2, 1),
            "thickness": round(thick, 1),
            "depth": round(depth, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_fr = min(thick / 2 - 0.5, 5.0)
            if max_fr >= 0.5:
                params["fillet_radius"] = round(rng.uniform(0.5, max_fr), 1)

        if difficulty == "hard":
            max_cl = min(depth / 4, 3.0)
            if max_cl >= 0.5:
                params["chamfer_length"] = round(rng.uniform(0.3, max_cl), 1)
            # Mounting holes on the horizontal arm surface
            max_hd = min(thick * 0.6, 6.0)
            if max_hd >= 2.0:
                params["hole_diameter"] = round(rng.uniform(2.0, max_hd), 1)
                # Hole position along horizontal arm (from inner corner)
                params["hole_offset_x"] = round(rng.uniform(arm1 * 0.3, arm1 * 0.7), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        """Validate L-bracket constraints."""
        a1 = params["arm1_length"]
        a2 = params["arm2_height"]
        t = params["thickness"]
        d = params["depth"]

        if a1 < 10 or a2 < 10:
            return False
        if t < 2:
            return False
        if d < 5:
            return False
        # Arms must be significantly longer than thickness
        if a1 <= t or a2 <= t:
            return False

        fr = params.get("fillet_radius")
        if fr is not None and fr >= t / 2:
            return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= d / 4:
            return False

        hd = params.get("hole_diameter")
        if hd is not None:
            if hd >= t:
                return False
            ox = params.get("hole_offset_x", 0)
            if ox <= hd / 2 + 1 or ox >= a1 - hd / 2 - 1:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        """Build program for L-bracket via bounding-box minus inner cutout."""
        difficulty = params.get("difficulty", "easy")
        a1 = params["arm1_length"]
        a2 = params["arm2_height"]
        t = params["thickness"]
        d = params["depth"]

        ops = []
        tags = {
            "has_hole": False,
            "has_fillet": False,
            "has_chamfer": False,
            "pattern_like": False,
        }

        # Bounding box: total_x = a1+t, total_y = a2+t, height = d
        # Centered at origin.  Inner cutout removes upper-right region.
        ops.append(Op("box", {"length": a1 + t, "width": a2 + t, "height": d}))

        # Cut inner corner: workplane on top face, shift to cutout center
        # Cutout center in workplane = (t/2, t/2), size = (a1, a2)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("center", {"x": round(t / 2, 4), "y": round(t / 2, 4)}))
        ops.append(Op("rect", {"length": a1, "width": a2}))
        ops.append(Op("cutThruAll", {}))

        # Fillet |Z edges (medium/hard) — all vertical edges of the L profile
        fr = params.get("fillet_radius")
        if fr is not None:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Chamfer bottom face outer edges (hard)
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Mounting hole on horizontal arm face (hard)
        hd = params.get("hole_diameter")
        ox = params.get("hole_offset_x")
        if hd is not None and ox is not None:
            tags["has_hole"] = True
            # Horizontal arm occupies y from -(a2+t)/2 to -(a2+t)/2 + t
            # Arm y-center in workplane: -(a2+t)/2 + t/2 = -(a2)/2 = -a2/2
            arm_y_center = round(-a2 / 2, 4)
            # ox is measured from inner corner (world x = t - (a1+t)/2 = -a1/2)
            # Hole world x = -a1/2 + ox
            arm_x = round(-a1 / 2 + ox, 4)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(arm_x, arm_y_center)]}))
            ops.append(Op("hole", {"diameter": hd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
