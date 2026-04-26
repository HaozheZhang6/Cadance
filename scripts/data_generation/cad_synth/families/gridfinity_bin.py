"""Gridfinity bin — popular 3D-printed modular storage system.

Base footprint uses 42 mm × 42 mm cells. Bin is a hollow shell open at top;
each cell of the base has a stacking lip. Simplified here as a rounded
rectangular shell with chamfered base (the lip) and a single inner pocket.

Keys: units_x × units_y (cell count), units_z (height in 7 mm stacks),
wall_t (wall thickness), label_lip (front label extension).

Easy:   1×1 bin.
Medium: 1×2 or 2×2 bin + label lip.
Hard:   2×3 bin + internal divider + base chamfer.

Reference: Gridfinity specification by Zack Freedman (open-source, community).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_CELL = 42.0
_STACK = 7.0  # each "unit" of height = 7 mm (≈ half of standard brick)


class GridfinityBinFamily(BaseFamily):
    name = "gridfinity_bin"
    standard = "N/A (open-source)"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            ux, uy = 1, 1
            uz = int(rng.choice([3, 4, 6]))
        elif difficulty == "medium":
            ux = int(rng.choice([1, 2]))
            uy = int(rng.choice([2, 2, 3]))
            uz = int(rng.choice([4, 6]))
        else:
            ux = int(rng.choice([2, 3]))
            uy = int(rng.choice([2, 3, 4]))
            uz = int(rng.choice([6, 8]))

        # Free wall_t and base_chamfer ratios (was hardcoded 1.6/1.6).
        wall_t = round(float(rng.uniform(1.2, 2.5)), 2)
        base_chamfer = round(float(rng.uniform(0.8, 2.5)), 2)
        params = {
            "units_x": ux,
            "units_y": uy,
            "units_z": uz,
            "cell_size": _CELL,
            "stack_h": _STACK,
            "wall_t": wall_t,
            "base_chamfer": base_chamfer,
            "base_edge_op": str(rng.choice(["chamfer", "fillet"])),
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["label_lip_h"] = round(float(rng.uniform(8.0, 16.0)), 1)
            params["label_lip_w"] = round(float(rng.uniform(10.0, 18.0)), 1)
        if difficulty == "hard" and ux * uy >= 4:
            params["divider"] = True
        return params

    def validate_params(self, params: dict) -> bool:
        if params["units_x"] < 1 or params["units_y"] < 1:
            return False
        if params["units_z"] < 2 or params["units_z"] > 12:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ux = params["units_x"]
        uy = params["units_y"]
        uz = params["units_z"]
        L = ux * _CELL
        W = uy * _CELL
        H = uz * _STACK
        wall = params["wall_t"]
        base_ch = params["base_chamfer"]

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": True,
            "rotational": False,
        }

        # Outer body: centered box
        ops = [
            Op(
                "box",
                {"length": round(L, 3), "width": round(W, 3), "height": round(H, 3)},
            ),
        ]
        # Base edge mod — chamfer or fillet on bottom edges (stacking lip).
        base_edge_op = params.get("base_edge_op", "chamfer")
        ops.append(Op("edges", {"selector": "<Z"}))
        if base_edge_op == "fillet":
            ops.append(Op("fillet", {"radius": base_ch}))
        else:
            ops.append(Op("chamfer", {"length": base_ch}))

        # Hollow inner pocket (from top): cut a box leaving wall_t around
        inner_L = L - 2 * wall
        inner_W = W - 2 * wall
        pocket_H = H - wall  # leave wall_t floor
        # Pocket top at z = H/2, bottom at z = -H/2 + wall
        pocket_cz = (H / 2) - pocket_H / 2
        ops.append(
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, pocket_cz],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "box",
                            "args": {
                                "length": round(inner_L, 3),
                                "width": round(inner_W, 3),
                                "height": round(pocket_H + 0.2, 3),
                            },
                        },
                    ],
                },
            )
        )

        # Label lip (medium+): small horizontal ledge at front top
        ll_h = params.get("label_lip_h")
        ll_w = params.get("label_lip_w")
        if ll_h and ll_w:
            lip_cy = -W / 2 + ll_w / 2 + wall
            lip_cz = H / 2 - ll_h / 2
            ops.append(
                Op(
                    "union",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, lip_cy, lip_cz],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(inner_L - 2, 3),
                                    "width": round(ll_w, 3),
                                    "height": round(ll_h * 0.25, 3),
                                },
                            },
                        ],
                    },
                )
            )

        # Divider (hard, only if footprint big enough)
        if params.get("divider") and inner_L > 20:
            ops.append(
                Op(
                    "union",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, pocket_cz],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(wall, 3),
                                    "width": round(inner_W, 3),
                                    "height": round(pocket_H * 0.9, 3),
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
