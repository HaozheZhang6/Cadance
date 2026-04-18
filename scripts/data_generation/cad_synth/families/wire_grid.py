"""Wire grid — flat grid of rectangular bars forming a mesh.

Distinct from mesh_panel (circular holes) and vented_panel (slots).
Represents: wire cooling rack, wire shelf, wire safety guard.

Easy:   flat grid (rectangular openings punched through a slab).
Medium: + chamfer on plate outer vertical edges.
Hard:   + raised border frame around the grid perimeter.
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class WireGridFamily(BaseFamily):
    name = "wire_grid"

    def sample_params(self, difficulty: str, rng) -> dict:
        wire_d = round(rng.uniform(2, 5), 1)
        n_x = int(rng.choice([3, 4, 5, 6]))
        n_y = int(rng.choice([2, 3, 4, 5]))
        cell_w = round(rng.uniform(10, 28), 1)
        cell_h = round(rng.uniform(10, 28), 1)

        width = round(n_x * cell_w + (n_x + 1) * wire_d, 1)
        height = round(n_y * cell_h + (n_y + 1) * wire_d, 1)

        params = {
            "wire_diameter": wire_d,
            "n_x": n_x,
            "n_y": n_y,
            "cell_width": cell_w,
            "cell_height": cell_h,
            "width": width,
            "height": height,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(wire_d * 0.3, 1.0), 1)

        if difficulty == "hard":
            params["frame_width"] = round(rng.uniform(4, 10), 1)
            params["frame_height"] = round(rng.uniform(6, 16), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        wd = params["wire_diameter"]
        cw = params["cell_width"]
        ch = params["cell_height"]
        W = params["width"]
        H = params["height"]

        if wd < 1.2:
            return False
        if cw < 6 or ch < 6:
            return False
        if W < 30 or H < 20:
            return False
        if cw <= wd or ch <= wd:
            return False

        chf = params.get("chamfer", 0)
        if chf and chf >= wd * 0.48:
            return False

        fw = params.get("frame_width", 0)
        fh = params.get("frame_height", 0)
        if fw and fw >= min(W, H) / 4:
            return False
        if fh and fh < 3:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        wd = params["wire_diameter"]
        n_x = params["n_x"]
        n_y = params["n_y"]
        cw = params["cell_width"]
        ch = params["cell_height"]
        W = params["width"]
        H = params["height"]

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # Flat slab (wire_d = slab thickness)
        ops.append(
            Op(
                "box",
                {"length": round(W, 4), "width": round(H, 4), "height": round(wd, 4)},
            )
        )

        # Chamfer vertical corner edges (medium+)
        chamfer = params.get("chamfer")
        if chamfer:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": chamfer}))

        # Cut rectangular openings (n_x columns × n_y rows)
        pts = []
        for i in range(n_x):
            cx = round(-W / 2 + wd + cw / 2 + i * (cw + wd), 4)
            for j in range(n_y):
                cy = round(-H / 2 + wd + ch / 2 + j * (ch + wd), 4)
                pts.append((cx, cy))

        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": pts}))
        ops.append(
            Op("rect", {"length": round(cw - 0.01, 4), "width": round(ch - 0.01, 4)})
        )
        ops.append(Op("cutThruAll", {}))

        # Raised border frame (hard): 4 bars along the perimeter edges
        frame_w = params.get("frame_width")
        frame_h = params.get("frame_height")
        if frame_w and frame_h:
            frame_cz = round(wd / 2 + frame_h / 2, 4)
            # Long sides (along X, at ±Y)
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
                                            round(sy * (H / 2 - frame_w / 2), 4),
                                            frame_cz,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(W, 4),
                                        "width": round(frame_w, 4),
                                        "height": round(frame_h, 4),
                                    },
                                },
                            ]
                        },
                    )
                )
            # Short sides (along Y, at ±X)
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
                                            round(sx * (W / 2 - frame_w / 2), 4),
                                            0.0,
                                            frame_cz,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(frame_w, 4),
                                        "width": round(H, 4),
                                        "height": round(frame_h, 4),
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
