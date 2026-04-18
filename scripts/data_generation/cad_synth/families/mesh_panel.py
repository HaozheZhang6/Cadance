"""Mesh panel — flat panel with regular grid of circular through-holes.

Represents: fan grille, speaker grille, drain cover, protective mesh panel.
Distinct from vented_panel (slots) and waffle_plate (raised ribs).

Easy:   flat panel + NxM circular hole grid.
Medium: + chamfer on panel edges.
Hard:   + solid frame border (slightly raised rim around the panel).
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class MeshPanelFamily(BaseFamily):
    name = "mesh_panel"

    def sample_params(self, difficulty: str, rng) -> dict:
        hole_d = round(rng.uniform(3, 10), 1)
        pitch_factor = round(rng.uniform(1.8, 3.0), 2)  # pitch / hole_d
        pitch = round(hole_d * pitch_factor, 1)
        n_cols = int(rng.choice([3, 4, 5, 6, 7]))
        n_rows = int(rng.choice([2, 3, 4, 5]))
        thickness = round(rng.uniform(3, 12), 1)

        # Panel size: grid extent + 1 pitch margin on each side
        panel_l = round((n_cols - 1) * pitch + 2 * pitch, 1)
        panel_w = round((n_rows - 1) * pitch + 2 * pitch, 1)

        params = {
            "hole_diameter": hole_d,
            "pitch": pitch,
            "n_cols": n_cols,
            "n_rows": n_rows,
            "thickness": thickness,
            "panel_length": panel_l,
            "panel_width": panel_w,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(thickness * 0.12, 1.5), 1)

        if difficulty == "hard":
            params["rim_height"] = round(rng.uniform(2, 6), 1)
            params["rim_width"] = round(rng.uniform(3, 8), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        hd = params["hole_diameter"]
        pitch = params["pitch"]
        t = params["thickness"]
        pl = params["panel_length"]
        pw = params["panel_width"]

        if pitch < hd * 1.5:
            return False
        if t < 2:
            return False
        if hd >= t * 1.5:  # hole diameter should be reasonable vs thickness
            return False
        if pl < 20 or pw < 15:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= t * 0.4:
            return False

        rh = params.get("rim_height", 0)
        rw = params.get("rim_width", 0)
        if rw and rw >= min(pl, pw) / 4:
            return False
        if rh and rh >= t * 2:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        hd = params["hole_diameter"]
        pitch = params["pitch"]
        n_cols = params["n_cols"]
        n_rows = params["n_rows"]
        t = params["thickness"]
        pl = params["panel_length"]
        pw = params["panel_width"]

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # Base panel
        ops.append(Op("box", {"length": pl, "width": pw, "height": t}))

        # Chamfer panel edges (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Grid of circular holes via rarray + circle + cutThruAll
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(
            Op(
                "rarray",
                {
                    "xSpacing": round(pitch, 4),
                    "ySpacing": round(pitch, 4),
                    "xCount": n_cols,
                    "yCount": n_rows,
                },
            )
        )
        ops.append(Op("circle", {"radius": round(hd / 2, 4)}))
        ops.append(Op("cutThruAll", {}))

        # Raised rim around panel (hard)
        rh = params.get("rim_height")
        rw = params.get("rim_width")
        if rh and rw:
            # Build 4 rim segments (outer frame, above panel top face)
            rim_center_z = round(t / 2 + rh / 2, 4)
            # Long sides
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
                                            round(sy * (pw / 2 - rw / 2), 4),
                                            rim_center_z,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(pl, 4),
                                        "width": round(rw, 4),
                                        "height": round(rh, 4),
                                    },
                                },
                            ]
                        },
                    )
                )
            # Short sides
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
                                            round(sx * (pl / 2 - rw / 2), 4),
                                            0.0,
                                            rim_center_z,
                                        ],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(rw, 4),
                                        "width": round(pw, 4),
                                        "height": round(rh, 4),
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
