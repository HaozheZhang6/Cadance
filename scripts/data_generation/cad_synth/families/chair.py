"""Chair — seat slab + four legs + vertical back panel.

Easy:   seat + 4 box legs + flat back panel.
Medium: + chamfer on seat top edges.
Hard:   + horizontal cross-bar on back.
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class ChairFamily(BaseFamily):
    name = "chair"

    def sample_params(self, difficulty: str, rng) -> dict:
        seat_l = round(rng.uniform(60, 160), 1)
        seat_w = round(rng.uniform(50, 120), 1)
        seat_t = round(rng.uniform(6, 20), 1)
        leg_w = round(rng.uniform(6, 16), 1)
        leg_h = round(rng.uniform(50, 150), 1)
        back_h = round(rng.uniform(40, 120), 1)
        back_t = round(rng.uniform(5, 14), 1)

        params = {
            "seat_length": seat_l,
            "seat_width": seat_w,
            "seat_thickness": seat_t,
            "leg_width": leg_w,
            "leg_height": leg_h,
            "back_height": back_h,
            "back_thickness": back_t,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(seat_t * 0.12, 1.5), 1)

        if difficulty == "hard":
            params["crossbar_height"] = round(back_h * rng.uniform(0.35, 0.65), 1)
            params["crossbar_thickness"] = round(leg_w * rng.uniform(0.7, 1.2), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        sl = params["seat_length"]
        sw = params["seat_width"]
        st = params["seat_thickness"]
        lw = params["leg_width"]
        lh = params["leg_height"]
        bh = params["back_height"]
        bt = params["back_thickness"]

        if lw * 3 >= sl or lw * 3 >= sw:
            return False
        if st < 4:
            return False
        if lh < 25 or bh < 20:
            return False
        if bt < 3:
            return False
        if bt >= sw * 0.3:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= st * 0.4:
            return False

        cb_h = params.get("crossbar_height", 0)
        cb_t = params.get("crossbar_thickness", 0)
        if cb_h and cb_h >= bh:
            return False
        if cb_t and cb_t >= bh * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        sl = params["seat_length"]
        sw = params["seat_width"]
        st = params["seat_thickness"]
        lw = params["leg_width"]
        lh = params["leg_height"]
        bh = params["back_height"]
        bt = params["back_thickness"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Seat slab (centered at origin): z from -st/2 to +st/2
        ops.append(Op("box", {"length": sl, "width": sw, "height": st}))

        # Chamfer top edges (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # 4 legs
        inset = lw / 2
        leg_cx = round(sl / 2 - inset, 4)
        leg_cy = round(sw / 2 - inset, 4)
        leg_center_z = round(-(st + lh) / 2, 4)

        for sx in (+1, -1):
            for sy in (+1, -1):
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [
                                            round(sx * leg_cx, 4),
                                            round(sy * leg_cy, 4),
                                            leg_center_z,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {"length": lw, "width": lw, "height": lh},
                                },
                            ]
                        },
                    )
                )

        # Back panel: at rear of seat (y = +sw/2 - bt/2 of the panel center),
        # extending upward from top of seat
        back_cx_z = round(st / 2 + bh / 2, 4)
        back_cy = round(sw / 2 - bt / 2, 4)
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, round(back_cy, 4), back_cx_z],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "box",
                            "args": {"length": sl, "width": bt, "height": bh},
                        },
                    ]
                },
            )
        )

        # Cross-bar on back (hard): horizontal bar at mid-height of back
        cb_h = params.get("crossbar_height")
        cb_t = params.get("crossbar_thickness")
        if cb_h and cb_t:
            # Bar center z = seat top + crossbar_height
            cb_z = round(st / 2 + cb_h, 4)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, round(back_cy, 4), cb_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": sl,
                                    "width": bt,
                                    "height": round(cb_t, 4),
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
