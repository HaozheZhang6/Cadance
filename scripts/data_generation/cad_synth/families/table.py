"""Table — flat top + four square legs.

Easy:   rectangular top slab + 4 box legs.
Medium: + chamfer on top edges.
Hard:   + apron boards (4 skirt panels connecting legs under the top).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class TableFamily(BaseFamily):
    name = "table"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        top_l = round(rng.uniform(100, 250), 1)
        top_w = round(rng.uniform(60, 160), 1)
        top_t = round(rng.uniform(8, 25), 1)
        leg_w = round(rng.uniform(8, 20), 1)
        leg_h = round(rng.uniform(60, 200), 1)

        params = {
            "top_length": top_l,
            "top_width": top_w,
            "top_thickness": top_t,
            "leg_width": leg_w,
            "leg_height": leg_h,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(top_t * 0.12, 2.0), 1)

        if difficulty == "hard":
            params["apron_thickness"] = round(leg_w * rng.uniform(0.8, 1.5), 1)
            params["apron_height"] = round(leg_h * rng.uniform(0.25, 0.45), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        tl = params["top_length"]
        tw = params["top_width"]
        tt = params["top_thickness"]
        lw = params["leg_width"]
        lh = params["leg_height"]

        if lw * 3 >= tl or lw * 3 >= tw:
            return False
        if tt < 4:
            return False
        if lh < 30:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= tt * 0.4:
            return False

        at = params.get("apron_thickness", 0)
        ah = params.get("apron_height", 0)
        if at and at >= lw * 2:
            return False
        if ah and ah >= lh * 0.6:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        tl = params["top_length"]
        tw = params["top_width"]
        tt = params["top_thickness"]
        lw = params["leg_width"]
        lh = params["leg_height"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Tabletop (centered at origin): z from -tt/2 to +tt/2
        ops.append(Op("box", {"length": tl, "width": tw, "height": tt}))

        # Chamfer top edges (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # 4 legs: corners just inset from tabletop edge
        inset = lw / 2
        leg_cx = tl / 2 - inset
        leg_cy = tw / 2 - inset
        leg_center_z = round(-(tt + lh) / 2, 4)

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

        # Apron boards (hard): 4 skirt panels under the top
        at = params.get("apron_thickness")
        ah = params.get("apron_height")
        if at and ah:
            apron_center_z = round(-(tt / 2 + ah / 2), 4)
            # Long sides (parallel to X)
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
                                            0.0,
                                            round(sy * (tw / 2 - at / 2), 4),
                                            apron_center_z,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(tl - 2 * lw, 4),
                                        "width": round(at, 4),
                                        "height": round(ah, 4),
                                    },
                                },
                            ]
                        },
                    )
                )
            # Short sides (parallel to Y)
            for sx in (+1, -1):
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [
                                            round(sx * (tl / 2 - at / 2), 4),
                                            0.0,
                                            apron_center_z,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(at, 4),
                                        "width": round(tw - 2 * lw, 4),
                                        "height": round(ah, 4),
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
