"""L-bracket family — two perpendicular arms joined at right angle (EN 10056).

EN 10056 equal-leg angle sections: leg × leg × thickness (mm).
Bracket arms correspond to angle legs; depth = bracket extrusion length.

Table: (leg_mm, thick_mm) from EN 10056-1 preferred sizes.

Reference: EN 10056-1:1998 — Equal and unequal leg angles; Table (leg, thickness for L20–L200)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# EN 10056-1 equal-leg angle sections — (leg_mm, thick_mm)
_EN10056_EQ = [
    (20, 3),
    (25, 3),
    (30, 3),
    (40, 4),
    (50, 5),
    (60, 5),
    (60, 6),
    (70, 7),
    (80, 8),
    (90, 9),
    (100, 10),
    (120, 11),
    (150, 12),
]
_SMALL = _EN10056_EQ[:5]  # leg 20–50
_MID = _EN10056_EQ[2:9]  # leg 30–80
_ALL = _EN10056_EQ


class LBracketFamily(BaseFamily):
    """EN 10056 equal-leg angle section bracket."""

    name = "l_bracket"
    standard = "EN 10056"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        leg, thick = pool[int(rng.integers(0, len(pool)))]
        arm1 = float(leg)
        arm2 = float(leg)  # equal legs per EN 10056
        depth_min = max(10.0, leg * 2)
        depth_max = max(depth_min + 10, leg * 8)
        depth = round(rng.uniform(depth_min, depth_max), 0)

        params = {
            "leg_size": float(leg),
            "arm1_length": arm1,
            "arm2_height": arm2,
            "thickness": float(thick),
            "depth": depth,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_fr = min(thick / 2 - 0.5, 5.0)
            if max_fr >= 0.5:
                params["fillet_radius"] = round(max_fr * 0.6, 1)

        if difficulty == "hard":
            # Mounting holes — standard bolt hole diameter = M_bolt ≈ 0.5 × thick
            hole_d = round(min(thick * 0.5, 8.0), 1)
            if hole_d >= 2.0:
                params["hole_diameter"] = hole_d
                params["hole_offset_x"] = round(arm1 * 0.5, 1)

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
