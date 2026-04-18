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

        if difficulty in ("medium", "hard"):
            gw = round(
                rng.uniform(2, max(2.5, min(r * 0.1, 5))), 1
            )  # ring groove width
            gd = round(
                rng.uniform(1.5, max(2.0, min(r * 0.08, 4))), 1
            )  # ring groove depth
            params["groove_width"] = gw
            params["groove_depth"] = gd

        if difficulty == "hard":
            # Wrist pin bore: horizontal cross hole at mid-skirt height
            pin_d = round(rng.uniform(r * 0.25, r * 0.55), 1)
            params["pin_diameter"] = pin_d
            params["pin_height"] = round(
                H * rng.uniform(0.15, 0.4), 1
            )  # height from bottom

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
        if gw and gd:
            if gd >= r * 0.15:
                return False
            if 2 * gw + 4 > ch:  # two grooves must fit in crown region
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

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        rv = round(r, 4)
        Hv = round(H, 4)

        if gw and gd:
            # Two ring grooves in crown region, spaced evenly
            # Groove positions (y from bottom): at H - ch + gw, H - ch + 3*gw
            y_groove1 = round(H - ch + gw, 4)
            y_groove2 = round(H - ch + 3 * gw, 4)
            r_bot = round(r - gd, 4)

            # Build profile with two grooves
            ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
            ops.append(Op("lineTo", {"x": rv, "y": 0.0}))
            ops.append(Op("lineTo", {"x": rv, "y": round(y_groove1 - gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": r_bot, "y": round(y_groove1 - gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": r_bot, "y": round(y_groove1 + gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": rv, "y": round(y_groove1 + gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": rv, "y": round(y_groove2 - gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": r_bot, "y": round(y_groove2 - gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": r_bot, "y": round(y_groove2 + gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": rv, "y": round(y_groove2 + gw / 2, 4)}))
            ops.append(Op("lineTo", {"x": rv, "y": Hv}))
            ops.append(Op("lineTo", {"x": 0.0, "y": Hv}))
            ops.append(Op("close", {}))
        else:
            # Easy: plain cylinder profile
            ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
            ops.append(Op("lineTo", {"x": rv, "y": 0.0}))
            ops.append(Op("lineTo", {"x": rv, "y": Hv}))
            ops.append(Op("lineTo", {"x": 0.0, "y": Hv}))
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
