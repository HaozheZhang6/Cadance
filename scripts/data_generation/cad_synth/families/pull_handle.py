"""Pull handle — round-bar grab/pull handle with mounting feet.

Two vertical riser legs + horizontal round bar on top. Mounting holes in the
feet for bolt-through attachment.

Keys: L (hole pitch center-to-center), H (grasp height), d (bar diameter).

Easy:   plain bar + posts (no foot).
Medium: + square foot pads with through-holes.
Hard:   + raised grip section (knurl region) represented by diameter step.

Reference: no active standard (DIN 81396 was withdrawn); hole-pitch L series
(80/100/120/160/200/250/300) and bar-d proportions follow common catalog
grab-handle ranges (Elesa, Kipp).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class PullHandleFamily(BaseFamily):
    name = "pull_handle"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            L = float(rng.choice([80, 100, 120]))
        elif difficulty == "medium":
            L = float(rng.choice([100, 120, 160, 200]))
        else:
            L = float(rng.choice([160, 200, 250, 300]))

        d_lo = max(8.0, L * 0.06)
        d_hi = max(d_lo + 2.0, min(25.0, L * 0.12))
        d = round(rng.uniform(d_lo, d_hi), 1)
        H_lo = max(30.0, d * 3.5)
        H_hi = max(H_lo + 5.0, min(100.0, L * 0.45))
        H = round(rng.uniform(H_lo, H_hi), 1)

        params = {
            "hole_pitch_L": L,
            "grasp_height_H": H,
            "bar_diameter_d": d,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            foot_side = round(d * 2.5, 1)
            foot_thick = round(d * 0.6, 1)
            hole_d = round(d * 0.6, 1)
            params.update(foot_side=foot_side, foot_thick=foot_thick, foot_hole=hole_d)
        if difficulty == "hard":
            params["grip_diameter"] = round(d * 1.35, 1)
            params["grip_length"] = round(L * 0.5, 1)
        return params

    def validate_params(self, params: dict) -> bool:
        L, H, d = (
            params["hole_pitch_L"],
            params["grasp_height_H"],
            params["bar_diameter_d"],
        )
        if d < 6 or H < d * 2 or L < d * 5:
            return False
        fs = params.get("foot_side", 0)
        if fs and fs <= d:
            return False
        gd = params.get("grip_diameter", 0)
        if gd and gd <= d:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        L = params["hole_pitch_L"]
        H = params["grasp_height_H"]
        d = params["bar_diameter_d"]
        r = round(d / 2, 3)

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout XY plane: risers along Z at x=±L/2, top bar along X at z=H.
        riser_L = H - r  # riser goes from z=0 to z=H-r (meeting underside of bar)
        ops = [
            Op(
                "transformed",
                {"offset": [-L / 2, 0, riser_L / 2], "rotate": [0, 0, 0]},
            ),
            Op("cylinder", {"height": round(riser_L, 3), "radius": r}),
        ]
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [L / 2, 0, riser_L / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(riser_L, 3), "radius": r},
                        },
                    ]
                },
            )
        )
        # Horizontal top bar along X, radius r, from x=-L/2 to x=+L/2 (plus cap)
        bar_len = L + d  # extends past risers by d/2 on each side
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, H - r],
                                "rotate": [0, 90, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(bar_len, 3), "radius": r},
                        },
                    ]
                },
            )
        )

        # Foot pads (medium+)
        fs = params.get("foot_side")
        ft = params.get("foot_thick")
        fh = params.get("foot_hole")
        if fs and ft:
            tags["has_hole"] = True
            for sign in (-1, 1):
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [sign * L / 2, 0, ft / 2],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(fs, 3),
                                        "width": round(fs, 3),
                                        "height": round(ft, 3),
                                    },
                                },
                            ]
                        },
                    )
                )
                if fh:
                    ops.append(
                        Op(
                            "cut",
                            {
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [sign * L / 2, 0, ft / 2],
                                            "rotate": [0, 0, 0],
                                        },
                                    },
                                    {
                                        "name": "cylinder",
                                        "args": {
                                            "height": round(ft + 2, 3),
                                            "radius": round(fh / 2, 3),
                                        },
                                    },
                                ]
                            },
                        )
                    )

        # Grip step (hard): larger cylinder around middle of bar
        gd = params.get("grip_diameter")
        gL = params.get("grip_length")
        if gd and gL:
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, H - r],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(gL, 3),
                                    "radius": round(gd / 2, 3),
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
