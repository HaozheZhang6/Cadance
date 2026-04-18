"""Manifold block — rectangular block with intersecting channel bores.

Structural type: box + multi-face directional boring.
Covers: hydraulic manifolds, pneumatic blocks, valve bodies, junction blocks.

variant=linear:   channels all from same face (parallel bores)
variant=cross:    channels from two perpendicular faces (intersecting)
variant=star:     channels from 4 faces meeting at center

Easy:   block + N parallel channels from top
Medium: + cross-channels from side face + counterbore ports
Hard:   + boss pads on port faces + chamfer
"""

from ..pipeline.builder import Op, Program
from ..pipeline.plane_utils import plane_offset
from .base import BaseFamily

VARIANTS = ["linear", "cross", "star"]


class ManifoldBlockFamily(BaseFamily):
    name = "manifold_block"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(VARIANTS)
        L = rng.uniform(40, 120)
        W = rng.uniform(30, max(30.1, L * 0.7))
        H = rng.uniform(25, max(25.1, L * 0.5))
        channel_d = rng.uniform(4, max(4.1, min(20, W * 0.25)))
        n_ch = int(rng.choice([2, 3, 4]))

        params = {
            "variant": variant,
            "length": round(L, 1),
            "width": round(W, 1),
            "height": round(H, 1),
            "channel_diameter": round(channel_d, 1),
            "n_channels": n_ch,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            cross_d = round(rng.uniform(3, max(3.1, min(channel_d * 0.9, 15))), 1)
            cbore_d = round(cross_d * rng.uniform(1.5, 2.2), 1)
            cbore_depth = round(rng.uniform(3, max(3.1, H * 0.2)), 1)
            params["cross_channel_diameter"] = cross_d
            params["cbore_diameter"] = cbore_d
            params["cbore_depth"] = cbore_depth

        if difficulty == "hard":
            pad_h = round(rng.uniform(3, max(3.1, H * 0.15)), 1)
            pad_d = round(channel_d * rng.uniform(2.0, 3.0), 1)
            params["port_pad_height"] = pad_h
            params["port_pad_diameter"] = pad_d
            params["chamfer_length"] = round(rng.uniform(0.5, 2.0), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        L = params["length"]
        W = params["width"]
        H = params["height"]
        cd = params["channel_diameter"]
        n = params["n_channels"]

        if cd >= W * 0.7 or cd >= H * 0.7:
            return False
        # channels must fit side by side
        spacing = L / (n + 1)
        if spacing < cd * 1.5:
            return False

        cbd = params.get("cbore_diameter")
        ccd = params.get("cross_channel_diameter")
        if cbd and ccd and cbd >= W * 0.6:
            return False
        if ccd and ccd >= H * 0.7:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bp = params.get("base_plane", "XY")
        variant = params.get("variant", "linear")
        L = params["length"]
        W = params["width"]
        H = params["height"]
        cd = params["channel_diameter"]
        n = params["n_channels"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # Base block
        ops.append(Op("box", {"length": L, "width": W, "height": H}))

        # Chamfer (hard) — BEFORE bores/bosses to avoid complex face selection
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Channel bores from top face
        spacing = round(L / (n + 1), 3)
        ch_pts = [(round(-L / 2 + spacing * (i + 1), 3), 0.0) for i in range(n)]
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("pushPoints", {"points": ch_pts}))
        ops.append(Op("hole", {"diameter": cd}))

        # Cross channels from front face (medium+)
        ccd = params.get("cross_channel_diameter")
        cbd = params.get("cbore_diameter")
        cbdep = params.get("cbore_depth")
        if ccd and cbd and cbdep:
            n_cross = max(1, n - 1)
            cross_spacing = round(H / (n_cross + 1), 3)
            cross_pts = [
                (round(-H / 2 + cross_spacing * (i + 1), 3), 0.0)
                for i in range(n_cross)
            ]
            ops.append(Op("faces", {"selector": ">Y"}))
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("pushPoints", {"points": cross_pts}))
            ops.append(
                Op(
                    "cboreHole",
                    {
                        "diameter": ccd,
                        "cboreDiameter": cbd,
                        "cboreDepth": cbdep,
                    },
                )
            )

        if variant == "star":
            # Additional channels from left and right faces
            ops.append(Op("faces", {"selector": ">X"}))
            ops.append(Op("workplane", {"selector": ">X"}))
            ops.append(Op("pushPoints", {"points": [(0.0, 0.0)]}))
            ops.append(Op("hole", {"diameter": cd}))

        # Boss pads (hard)
        pad_h = params.get("port_pad_height")
        pad_d = params.get("port_pad_diameter")
        if pad_h and pad_d:
            pr = round(pad_d / 2, 3)
            for cx, _ in ch_pts[:2]:  # pads on first 2 ports
                ops.append(
                    Op(
                        "union",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": plane_offset(
                                            bp, cx, 0, round(H / 2 + pad_h / 2 - 0.5, 3)
                                        ),
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {"height": pad_h, "radius": pr},
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
