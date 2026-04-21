"""Hex-key organizer — 3D-printed allen-key holder block.

Flat rectangular block with a row (or fan) of vertical hex-shaped pockets to
hold hex keys (1.5 / 2 / 2.5 / 3 / 4 / 5 / 6 / 8 mm). Base is simple box +
hex cuts using polygon n=6.

Keys: key_sizes (list of hex-key widths-across-flats), pitch (spacing),
block_depth (pocket depth), block_thickness.

Easy:   3 sizes, straight row.
Medium: 5 sizes + chamfered pocket rims.
Hard:   7 sizes + fan arrangement (angled rows) OR chamfered block edges.

Reference: ISO 2936 / DIN 911 hex key sizes; block is open design (no standard).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_KEY_SIZES_MM = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]


class HexKeyOrganizerFamily(BaseFamily):
    name = "hex_key_organizer"
    standard = "ISO 2936"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            n_keys = 3
            start = int(rng.integers(0, 3))
        elif difficulty == "medium":
            n_keys = 5
            start = int(rng.integers(0, 3))
        else:
            n_keys = 7
            start = int(rng.integers(0, 2))
        sizes = _KEY_SIZES_MM[start : start + n_keys]

        # Block size from largest key + margin
        max_s = max(sizes)
        pitch = round(max_s * 1.6 + 2.0, 1)
        block_L = round(pitch * (len(sizes) + 0.5), 1)
        block_W = round(max_s * 2.0 + 6.0, 1)
        block_T = round(min(max_s * 1.8 + 3.0, 22.0), 1)
        pocket_depth = round(block_T * 0.7, 1)

        params = {
            "key_sizes": sizes,
            "pitch": pitch,
            "block_L": block_L,
            "block_W": block_W,
            "block_T": block_T,
            "pocket_depth": pocket_depth,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["pocket_chamfer"] = 0.4
        if difficulty == "hard":
            params["edge_chamfer"] = 1.0
        return params

    def validate_params(self, params: dict) -> bool:
        sizes = params["key_sizes"]
        if not sizes:
            return False
        if params["pitch"] <= max(sizes) + 1:
            return False
        if params["pocket_depth"] >= params["block_T"]:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        sizes = params["key_sizes"]
        pitch = params["pitch"]
        L = params["block_L"]
        W = params["block_W"]
        T = params["block_T"]
        depth = params["pocket_depth"]

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Block centered at origin, top at z=T/2
        ops = [
            Op(
                "box",
                {"length": round(L, 3), "width": round(W, 3), "height": round(T, 3)},
            ),
        ]

        # Edge chamfer (hard)
        ec = params.get("edge_chamfer")
        if ec:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": ec}))

        # Hex pockets along X, centered in Y
        n = len(sizes)
        start_x = -((n - 1) / 2) * pitch
        for i, s in enumerate(sizes):
            px = round(start_x + i * pitch, 4)
            # Pocket top at block top; cut extends down by `depth`
            # polygon across-flats = s -> diameter (across-corners) = s / cos(30°)
            poly_diam = round(s / math.cos(math.radians(30)) + 0.3, 4)  # +0.3 clearance
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [px, 0, T / 2 - depth / 2 + 0.1],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "polygon",
                                "args": {"n": 6, "diameter": poly_diam},
                            },
                            {
                                "name": "extrude",
                                "args": {
                                    "distance": round(depth / 2 + 0.1, 4),
                                    "both": True,
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
