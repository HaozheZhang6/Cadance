"""Phone stand — 3D-printed desk phone/tablet holder.

L-shaped wedge: flat base + angled back rest. Front lip retains phone; slot
through base/back for charging cable.

Keys: base_L (depth), base_W (width), back_H (rest height), back_angle,
lip_h (front lip), cable_slot_w.

Easy:   pure angled wedge (base + sloped back, no lip/slot).
Medium: + front lip + charging cable slot through back.
Hard:   + rounded edges + bottom relief pocket for weight savings.

Reference: No formal standard — common 3D-print community pattern.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class PhoneStandFamily(BaseFamily):
    name = "phone_stand"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            base_L = round(rng.uniform(55.0, 75.0), 1)
            back_H = round(rng.uniform(70.0, 95.0), 1)
            angle = round(rng.uniform(55.0, 70.0), 1)
            thick = round(rng.uniform(4.0, 6.0), 1)
        elif difficulty == "medium":
            base_L = round(rng.uniform(70.0, 90.0), 1)
            back_H = round(rng.uniform(90.0, 120.0), 1)
            angle = round(rng.uniform(60.0, 72.0), 1)
            thick = round(rng.uniform(4.5, 6.5), 1)
        else:
            base_L = round(rng.uniform(85.0, 110.0), 1)
            back_H = round(rng.uniform(110.0, 140.0), 1)
            angle = round(rng.uniform(65.0, 75.0), 1)
            thick = round(rng.uniform(5.0, 7.0), 1)

        base_W = round(rng.uniform(65.0, 95.0), 1)
        params = {
            "base_depth": base_L,
            "base_width": base_W,
            "back_height": back_H,
            "back_angle_deg": angle,
            "shell_thickness": thick,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["front_lip_h"] = round(rng.uniform(8.0, 14.0), 1)
            params["cable_slot_w"] = round(rng.uniform(14.0, 22.0), 1)
        if difficulty == "hard":
            # Relief pocket under base (material savings, common print optimization)
            params["relief_pocket_L"] = round(base_L * 0.55, 1)
            params["relief_pocket_W"] = round(base_W * 0.55, 1)
            params["relief_pocket_D"] = round(thick * 0.5, 1)
        return params

    def validate_params(self, params: dict) -> bool:
        if params["base_depth"] < 40 or params["base_width"] < 50:
            return False
        if params["back_height"] < 50:
            return False
        if params["back_angle_deg"] < 45 or params["back_angle_deg"] > 85:
            return False
        if params["shell_thickness"] < 3:
            return False
        slw = params.get("cable_slot_w", 0)
        if slw and slw >= params["base_width"] * 0.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        base_L = params["base_depth"]
        base_W = params["base_width"]
        back_H = params["back_height"]
        angle = params["back_angle_deg"]
        t = params["shell_thickness"]

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout:
        #   Base slab lies on XY plane, centered on origin, z=[0, t].
        #   Back rest is another slab tilted `angle` degrees from horizontal,
        #   hinged at the BACK edge of the base (y = +base_L/2).
        # Build as two separate slabs unioned.

        # Base slab
        ops = [
            Op(
                "transformed",
                {"offset": [0, 0, t / 2], "rotate": [0, 0, 0]},
            ),
            Op(
                "box",
                {
                    "length": round(base_W, 3),
                    "width": round(base_L, 3),
                    "height": round(t, 3),
                },
            ),
        ]

        # Back rest: a slab of dims (base_W × t × back_H) tilted around X axis.
        # Rotate the workplane by (90 - angle) around X so the slab's local Z
        # direction (normally up) now points in +Y,+Z diagonal.
        # Place pivot at (0, base_L/2, t) — back edge of base, top surface.
        # Then translate the slab along its local +Z (up the rest) by back_H/2.
        tilt = 90.0 - angle  # degrees from vertical
        # Local frame after rotate: the slab's height direction makes angle with Y.
        # We'll offset the workplane to the pivot, rotate, then offset by half
        # the slab height along local +Y.
        # Decompose: in a separate union Op.
        pivot_y = base_L / 2
        # Compute offset in pre-rotate world frame: we want the slab's base
        # centered on (0, pivot_y, t), and slab extends upward tilted.
        # Since rotate is around X at origin of transformed wp, we translate
        # first to pivot, then rotate, then shift along local +Z by back_H/2.
        # Pivot at base BOTTOM so back rest passes through full base thickness
        # and fuses with base.
        rest_h = back_H + t
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, pivot_y, 0],
                                "rotate": [-tilt, 0, 0],
                            },
                        },
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, rest_h / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "box",
                            "args": {
                                "length": round(base_W, 3),
                                "width": round(t, 3),
                                "height": round(rest_h, 3),
                            },
                        },
                    ],
                },
            )
        )

        # Front lip (medium+): ridge along front edge of base
        lip_h = params.get("front_lip_h")
        if lip_h:
            lip_y = -base_L / 2 + t / 2
            lip_cz = t + lip_h / 2
            ops.append(
                Op(
                    "union",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, lip_y, lip_cz],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(base_W, 3),
                                    "width": round(t, 3),
                                    "height": round(lip_h, 3),
                                },
                            },
                        ],
                    },
                )
            )

        # Cable slot (medium+): rectangular cut through base near back edge
        slw = params.get("cable_slot_w")
        if slw:
            tags["has_slot"] = True
            # Cut through base at the pivot line
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, pivot_y - t, t / 2],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(slw, 3),
                                    "width": round(t * 1.5, 3),
                                    "height": round(t * 2 + 0.5, 3),
                                },
                            },
                        ],
                    },
                )
            )
            # Also cut through back rest bottom (along sloped face)
            slot_back_z = t + slw * 0.8 / math.cos(math.radians(90 - angle))
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, pivot_y, slot_back_z / 2 + t],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(slw, 3),
                                    "width": round(t * 3.0, 3),
                                    "height": round(slot_back_z, 3),
                                },
                            },
                        ],
                    },
                )
            )

        # Relief pocket under base (hard): cut upward from bottom face
        rpL = params.get("relief_pocket_L")
        rpW = params.get("relief_pocket_W")
        rpD = params.get("relief_pocket_D")
        if rpL and rpW and rpD:
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, rpD / 2],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(rpW, 3),
                                    "width": round(rpL, 3),
                                    "height": round(rpD + 0.1, 3),
                                },
                            },
                        ],
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
