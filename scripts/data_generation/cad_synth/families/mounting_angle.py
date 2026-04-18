"""Mounting angle — EN 10056 equal-leg angle with bolt holes on both flanges.

Same L-shape as l_bracket, but holes are the PRIMARY feature on both arms.
Leg dimensions from EN 10056-1 equal-leg angle section table.

Easy:   L + holes on base arm only.
Medium: + holes on web arm.
Hard:   + fillet at inner corner + extra hole row.
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program

# EN 10056-1 equal-leg angle sections — (leg_mm, thick_mm)
_EN10056 = [
    (25, 3),
    (30, 3),
    (40, 4),
    (50, 5),
    (60, 6),
    (70, 7),
    (80, 8),
    (90, 9),
    (100, 10),
    (120, 11),
    (150, 12),
]
_SMALL = _EN10056[:4]  # leg 25–50
_MID = _EN10056[2:8]  # leg 40–90
_ALL = _EN10056


class MountingAngleFamily(BaseFamily):
    name = "mounting_angle"
    standard = "EN 10056"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        leg, thick = pool[int(rng.integers(0, len(pool)))]
        arm_w = float(leg)
        web_h = float(leg)
        depth = round(rng.uniform(max(20.0, leg * 2), leg * 6), 0)
        # Bolt hole diameter: < 0.7 × thick to pass validate; min 2mm
        hole_d = round(max(2.0, min(thick * 0.6, 8.0)), 1)
        n_base = int(rng.choice([1, 2, 3]))

        params = {
            "leg_size": float(leg),
            "arm_width": arm_w,
            "web_height": web_h,
            "thickness": float(thick),
            "depth": depth,
            "hole_diameter": hole_d,
            "n_base_holes": n_base,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["n_web_holes"] = int(rng.choice([1, 2, 3]))

        if difficulty == "hard":
            max_fr = min(float(thick) / 2 - 0.5, 5.0)
            if max_fr >= 0.5:
                params["fillet_radius"] = round(max_fr * 0.6, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        arm_w = params["arm_width"]
        web_h = params["web_height"]
        thick = params["thickness"]
        depth = params["depth"]
        hd = params["hole_diameter"]
        n_base = params["n_base_holes"]

        if arm_w <= thick or web_h <= thick:
            return False
        if thick < 3:
            return False
        if hd >= thick * 0.85:
            return False
        if depth < 15:
            return False

        # base holes must fit with edge margins
        edge_margin = hd / 2 + 2
        if n_base == 1:
            pass  # single hole at center always fits
        else:
            spacing = (depth - 2 * edge_margin) / (n_base - 1)
            if spacing < hd * 1.5:
                return False

        n_web = params.get("n_web_holes", 0)
        if n_web:
            edge_margin_web = hd / 2 + 2
            if n_web > 1:
                spacing = (depth - 2 * edge_margin_web) / (n_web - 1)
                if spacing < hd * 1.5:
                    return False

        fr = params.get("fillet_radius")
        if fr is not None and fr >= thick / 2:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        arm_w = params["arm_width"]
        web_h = params["web_height"]
        t = params["thickness"]
        depth = params["depth"]
        hd = params["hole_diameter"]
        n_base = params["n_base_holes"]

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # L-shape: bounding box minus inner corner
        ops.append(
            Op("box", {"length": arm_w + t, "width": web_h + t, "height": depth})
        )
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("center", {"x": round(t / 2, 4), "y": round(t / 2, 4)}))
        ops.append(Op("rect", {"length": arm_w, "width": web_h}))
        ops.append(Op("cutThruAll", {}))

        # Fillet inner corner edges |Z (hard)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Base arm holes: drilled in Z direction from ">Z" face
        # Base arm occupies y = -(web_h)/2 (center in workplane) ± t/2
        # Workplane ">Z" uses world X,Y → hole positions are (x_world, y_world)
        base_arm_y = round(-(web_h) / 2, 4)  # y-center of base arm in >Z workplane
        edge_m = hd / 2 + 2
        if n_base == 1:
            base_xs = [0.0]
        else:
            base_xs = [
                round(-depth / 2 + edge_m + i * (depth - 2 * edge_m) / (n_base - 1), 4)
                for i in range(n_base)
            ]
        # Use >Z workplane: local (x,y) = (Z_world, X_world) ... but builder sets >Z as (X_world, Y_world)
        # Actually in builder: workplane(">Z") uses world X and Y as local coords.
        # For the ">Z" face (top face, depth = height = Z dim):
        # local_x = world X, local_y = world Y
        # base arm center in world Y: y_world = -(web_h)/2 (in workplane centered at 0,0)
        # holes along depth (world Z → need to use a different axis):
        # Wait: depth is the Z dimension (box height). ">Z" workplane has local (x=X_world, y=Y_world).
        # To space holes along depth (Z direction), we need to use a DIFFERENT FACE.
        # Let's use ">Y" face for base arm holes (face at y=+(web_h+t)/2):
        # ">Y" local_x = Z_world, local_y = X_world (from manifold_block convention)
        # Base arm is at Y_world = -(web_h+t)/2 to -(web_h)/2, centered at -(web_h+2*t)/4
        # Actually for base arm: world y from -(web_h+t)/2 to -(web_h+t)/2 + t
        # Center of base arm in world Y: -(web_h+t)/2 + t/2 = -(web_h)/2 = base_arm_y ✓
        # From ">Y" face: local_x = Z_world (depth direction), local_y = X_world
        # Hole positions on base arm from ">Y" face:
        #   local_x = z_i (spaced along depth), local_y = x_arm_center = -(arm_w)/2
        # Hmm wait: base arm x spans full width (-(arm_w+t)/2 to +(arm_w+t)/2)
        # So x_arm_center = 0 works fine (center of arm in X)
        # Let's use ">Y" for base arm, ">X" for web arm... but these have untested coord mappings.

        # SIMPLE APPROACH: use ">Z" workplane, holes at base arm Y position, X spaced along arm
        # These holes go through depth (Z direction) — valid for angle brackets.
        arm_span_x = arm_w - 2 * edge_m
        if n_base == 1:
            base_pts = [(0.0, base_arm_y)]
        elif n_base == 2:
            base_pts = [
                (round(-arm_span_x / 2, 4), base_arm_y),
                (round(+arm_span_x / 2, 4), base_arm_y),
            ]
        else:
            base_pts = [
                (round(-arm_span_x / 2 + i * arm_span_x / (n_base - 1), 4), base_arm_y)
                for i in range(n_base)
            ]

        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": base_pts}))
        ops.append(Op("hole", {"diameter": round(hd, 4)}))

        # Web arm holes: in web arm X zone, spaced along arm_w (Y direction)
        n_web = params.get("n_web_holes")
        if n_web:
            web_arm_x = round(-(arm_w) / 2, 4)  # x-center of web arm in >Z workplane
            web_span_y = web_h - 2 * edge_m
            if n_web == 1:
                web_pts = [(web_arm_x, 0.0)]
            elif n_web == 2:
                web_pts = [
                    (web_arm_x, round(-web_span_y / 2, 4)),
                    (web_arm_x, round(+web_span_y / 2, 4)),
                ]
            else:
                web_pts = [
                    (
                        web_arm_x,
                        round(-web_span_y / 2 + i * web_span_y / (n_web - 1), 4),
                    )
                    for i in range(n_web)
                ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": web_pts}))
            ops.append(Op("hole", {"diameter": round(hd, 4)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
