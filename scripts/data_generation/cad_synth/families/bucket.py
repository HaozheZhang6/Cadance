"""Bucket — hollow truncated cone with closed bottom, open top.

Profile revolved 360° around Y axis (XY_ONLY).
Wider at top than bottom (taper for stacking).

Easy:   hollow frustum + closed bottom.
Medium: + chamfer on top rim.
Hard:   + two rectangular handle-attachment bosses at top.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class BucketFamily(BaseFamily):
    name = "bucket"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        r_bot = round(rng.uniform(40, 100), 1)
        r_top = round(r_bot * rng.uniform(1.1, 1.4), 1)
        height = round(rng.uniform(80, 200), 1)
        wall = round(rng.uniform(3, min(r_bot * 0.1, 8)), 1)
        bottom_t = round(wall * rng.uniform(1.0, 1.5), 1)

        params = {
            "r_bottom": r_bot,
            "r_top": r_top,
            "height": height,
            "wall_thickness": wall,
            "bottom_thickness": bottom_t,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["top_chamfer"] = round(min(wall * 0.4, 2.5), 1)

        if difficulty == "hard":
            params["boss_width"] = round(rng.uniform(10, 22), 1)
            params["boss_height"] = round(rng.uniform(15, 32), 1)
            params["boss_depth"] = round(rng.uniform(4, 9), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r_bot = params["r_bottom"]
        r_top = params["r_top"]
        h = params["height"]
        wall = params["wall_thickness"]
        bt = params["bottom_thickness"]

        if r_top <= r_bot:
            return False
        if r_bot - wall < 10:
            return False
        if wall < 2:
            return False
        if bt < 2:
            return False
        if h < 50:
            return False

        tc = params.get("top_chamfer", 0)
        if tc and tc >= wall * 0.8:
            return False

        bw = params.get("boss_width", 0)
        bh = params.get("boss_height", 0)
        if bw and bw >= r_top * 0.6:
            return False
        if bh and bh >= h * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r_bot = params["r_bottom"]
        r_top = params["r_top"]
        H = params["height"]
        wall = params["wall_thickness"]
        bt = params["bottom_thickness"]

        r_bot_inner = round(r_bot - wall, 4)
        r_top_inner = round(r_top - wall, 4)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # 2D profile in XY plane, revolved around Y axis [0,1,0]:
        #   x = radial distance (≥0), y = height (0=bottom, H=top)
        # Outer taper + inner taper + closed bottom disk
        ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
        ops.append(Op("lineTo", {"x": round(r_bot, 4), "y": 0.0}))
        ops.append(Op("lineTo", {"x": round(r_top, 4), "y": round(H, 4)}))
        ops.append(Op("lineTo", {"x": round(r_top_inner, 4), "y": round(H, 4)}))
        ops.append(Op("lineTo", {"x": round(r_bot_inner, 4), "y": round(bt, 4)}))
        ops.append(Op("lineTo", {"x": 0.0, "y": round(bt, 4)}))
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

        # Chamfer top rim (medium+)
        tc = params.get("top_chamfer")
        if tc:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Y"}))
            ops.append(Op("chamfer", {"length": round(tc, 4)}))

        # Handle attachment bosses: two rectangular pads at ±X, near top (hard)
        bw = params.get("boss_width")
        bh = params.get("boss_height")
        bd = params.get("boss_depth")
        if bw and bh and bd:
            for sx in (+1, -1):
                boss_cx = round(sx * (r_top + bd / 2), 4)
                boss_cy = round(H - bh / 2, 4)
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [boss_cx, boss_cy, 0.0],
                                        "rotate": [0.0, 0.0, 0.0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(bd, 4),
                                        "width": round(bh, 4),
                                        "height": round(bw, 4),
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
