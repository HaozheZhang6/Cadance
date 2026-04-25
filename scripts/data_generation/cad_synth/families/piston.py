"""Piston — cylindrical engine/pump piston with ring grooves.

Profile revolved 360° around Y axis (XY_ONLY).
x = radial distance, y = axial height (0 = bottom of skirt, H = crown top).

Easy:   plain cylinder body (revolve rectangle).
Medium: + 2 piston ring grooves cut into the OD near the crown.
Hard:   + wrist-pin cross bore through the lower skirt.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class PistonFamily(BaseFamily):
    name = "piston"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        r = round(rng.uniform(20, 70), 1)  # piston radius
        H = round(rng.uniform(40, 120), 1)  # total height (skirt + crown)
        crown_h = round(rng.uniform(H * 0.25, H * 0.5), 1)  # crown region height

        params = {
            "radius": r,
            "height": H,
            "crown_height": crown_h,
            "difficulty": difficulty,
        }

        groove_prob = {"easy": 0.2, "medium": 0.8, "hard": 0.9}[difficulty]
        pin_prob = {"easy": 0.0, "medium": 0.3, "hard": 0.85}[difficulty]
        params["profile_reverse"] = bool(rng.random() < 0.5)

        if rng.random() < groove_prob:
            gw = round(
                rng.uniform(2, max(2.5, min(r * 0.1, 5))), 1
            )  # ring groove width
            gd = round(
                rng.uniform(1.5, max(2.0, min(r * 0.08, 4))), 1
            )  # ring groove depth
            params["groove_width"] = gw
            params["groove_depth"] = gd
            # Variable groove count 1/2/3 (was fixed 2)
            params["n_grooves"] = int(rng.choice([1, 2, 3]))

        if rng.random() < pin_prob:
            pin_d = round(rng.uniform(r * 0.25, r * 0.55), 1)
            params["pin_diameter"] = pin_d
            params["pin_height"] = round(H * rng.uniform(0.15, 0.4), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r = params["radius"]
        H = params["height"]
        ch = params["crown_height"]

        if r < 12:
            return False
        if H < 25:
            return False
        if ch < 10 or ch >= H * 0.65:
            return False

        gw = params.get("groove_width", 0)
        gd = params.get("groove_depth", 0)
        ng = int(params.get("n_grooves", 0))
        if gw and gd:
            if gd >= r * 0.15:
                return False
            if ng * gw + (ng + 1) * 1.0 > ch:
                return False

        pd = params.get("pin_diameter", 0)
        ph = params.get("pin_height", 0)
        if pd:
            if pd >= r * 0.7:
                return False
            if ph and ph + pd / 2 >= H - ch:  # pin must stay in skirt
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r = params["radius"]
        H = params["height"]
        ch = params["crown_height"]

        gw = params.get("groove_width", 0)
        gd = params.get("groove_depth", 0)
        n_grooves = int(params.get("n_grooves", 0))

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        rv = round(r, 4)
        Hv = round(H, 4)

        # Build profile: bottom (0,0) → outer (r,0) → up with N grooves → (r,H) → (0,H).
        pts = [(0.0, 0.0), (rv, 0.0)]
        if gw and gd and n_grooves > 0:
            r_bot = round(r - gd, 4)
            spacing = ch / (n_grooves + 1)
            for i in range(n_grooves):
                y_g = round(H - ch + spacing * (i + 1), 4)
                pts.append((rv, round(y_g - gw / 2, 4)))
                pts.append((r_bot, round(y_g - gw / 2, 4)))
                pts.append((r_bot, round(y_g + gw / 2, 4)))
                pts.append((rv, round(y_g + gw / 2, 4)))
        pts.append((rv, Hv))
        pts.append((0.0, Hv))

        if params.get("profile_reverse", False):
            pts = list(reversed(pts))

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
                    "axisEnd": [0, 1, 0],
                },
            )
        )

        # Wrist-pin cross bore (hard): workplane at pin height, circle, cutThruAll along Z.
        # In XY base plane, cutThruAll cuts along Z — perpendicular to piston axis Y.
        pd = params.get("pin_diameter")
        ph = params.get("pin_height")
        if pd and ph:
            tags["has_hole"] = True
            ops.append(
                Op(
                    "transformed",
                    {"offset": [0.0, round(ph, 4), 0.0], "rotate": [0, 0, 0]},
                )
            )
            ops.append(Op("circle", {"radius": round(pd / 2, 4)}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
