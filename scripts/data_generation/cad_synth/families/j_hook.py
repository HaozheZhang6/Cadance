"""J-hook — pipe/cable hanger hook (open half of a U-bolt).

One straight threaded leg + a semicircular hook (half-torus). Like a U-bolt
cut in half: threaded leg on one side, open hook on the other.

Keys: D (hook inner diameter), d (rod diameter), b (thread length), L (total leg).

Easy:   straight rod + half-torus hook (no plate, no threads).
Medium: + welded square backing plate (fused to leg tip, no through-hole —
        holes are skipped to keep plate + hook as one connected solid).
Hard:   + hex nut welded onto leg tip (threads not supported for offset legs
        in this pipeline — the helix sweep axis is world-Z-fixed).

Reference: no active geometric standard; rod-d ∈ {6,8,10,12,16 mm} and hook
inner diameter chosen to mate common DN pipe sizes.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# (rod_d, hook_ID, leg_L, total_L)
_J_HOOK_SIZES = [
    (6.0, 20.0, 40.0, 70.0),
    (8.0, 30.0, 55.0, 95.0),
    (10.0, 40.0, 70.0, 120.0),
    (12.0, 50.0, 90.0, 150.0),
    (12.0, 65.0, 110.0, 185.0),
    (16.0, 80.0, 130.0, 220.0),
]

_ISO261_PITCH = {6: 1.0, 8: 1.25, 10: 1.5, 12: 1.75, 16: 2.0}


class JHookFamily(BaseFamily):
    name = "j_hook"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _J_HOOK_SIZES[:3]
        elif difficulty == "medium":
            pool = _J_HOOK_SIZES[1:5]
        else:
            pool = _J_HOOK_SIZES[3:]

        rod_d, hook_id, leg_L, total_L = pool[int(rng.integers(0, len(pool)))]
        params = {
            "rod_d": float(rod_d),
            "hook_inner_D": float(hook_id),
            "leg_length": float(leg_L),
            "total_length": float(total_L),
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            plate_side = round(rod_d * 3.5, 1)
            plate_t = round(max(3.0, rod_d * 0.4), 1)
            hole_d = round(rod_d + 1.5, 1)
            params.update(plate_side=plate_side, plate_t=plate_t, hole_d=hole_d)
        if difficulty == "hard":
            params["hex_nut_af"] = round(rod_d * 1.5, 2)
            params["hex_nut_h"] = round(rod_d * 0.8, 2)
        return params

    def validate_params(self, params: dict) -> bool:
        rod_d = params["rod_d"]
        D = params["hook_inner_D"]
        L = params["leg_length"]
        if rod_d < 4 or D < rod_d * 2 or L < rod_d * 2:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rod_r = params["rod_d"] / 2
        hook_R = params["hook_inner_D"] / 2 + rod_r  # centerline radius
        leg_L = params["leg_length"]

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout: straight leg at x=+hook_R, tip at z=0, going up to z=leg_L.
        # Half-torus hook at z=leg_L, centerline radius=hook_R, sweeping from
        # x=+hook_R through -X through +Z then back... actually: half-torus
        # from (+hook_R, 0, leg_L) around to (-hook_R, 0, leg_L) going through
        # (0, 0, leg_L + hook_R). Then free hook end at (-hook_R, 0, leg_L)
        # is NOT connected (that's the "J" open end).
        # If plate is present, leg extends DOWN through plate so they fuse.
        overlap = rod_r * 0.5
        pT_val = params.get("plate_t", 0) or 0
        leg_z_bot = -pT_val if pT_val else 0.0
        leg_top = leg_L + overlap
        leg_full = leg_top - leg_z_bot

        # Straight leg
        ops = [
            Op(
                "transformed",
                {
                    "offset": [hook_R, 0.0, (leg_z_bot + leg_top) / 2],
                    "rotate": [0, 0, 0],
                },
            ),
            Op("cylinder", {"height": round(leg_full, 3), "radius": round(rod_r, 3)}),
        ]
        # Half-torus hook (top) at z=leg_L, major=hook_R, minor=rod_r, 180°
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, round(leg_L, 3)],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "moveTo", "args": {"x": round(hook_R, 3), "y": 0.0}},
                        {"name": "circle", "args": {"radius": round(rod_r, 3)}},
                        {
                            "name": "revolve",
                            "args": {
                                "angleDeg": 180,
                                "axisStart": [0, 0, 0],
                                "axisEnd": [0, -1, 0],
                            },
                        },
                    ],
                },
            )
        )

        # Backing plate (medium+) at tip
        ps = params.get("plate_side")
        pt = params.get("plate_t")
        hd = params.get("hole_d")
        if ps and pt:
            plate_z = -pt / 2
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [hook_R, 0, plate_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(ps, 3),
                                    "width": round(ps, 3),
                                    "height": round(pt, 3),
                                },
                            },
                        ]
                    },
                )
            )

        # Hex nut welded onto leg tip (hard)
        af = params.get("hex_nut_af")
        nh = params.get("hex_nut_h")
        if af and nh:
            nut_cz = leg_z_bot - nh / 2 + 0.5
            r_hex = af / 2
            hex_pts = []
            for k in range(6):
                ang = math.radians(30 + k * 60)
                hex_pts.append(
                    [round(r_hex * math.cos(ang), 4), round(r_hex * math.sin(ang), 4)]
                )
            ops.append(
                Op(
                    "union",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [hook_R, 0.0, nut_cz],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "moveTo",
                                "args": {"x": hex_pts[0][0], "y": hex_pts[0][1]},
                            },
                            {"name": "polyline", "args": {"points": hex_pts[1:]}},
                            {"name": "close"},
                            {
                                "name": "extrude",
                                "args": {"distance": round(nh / 2, 4), "both": True},
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
