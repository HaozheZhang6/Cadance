"""Dovetail slide / linear guide — two variants.

variant=male:   trapezoidal tongue bar (slides into female groove)
variant=female: rectangular block with dovetail groove cut along length

Cross-section conventions (XY plane, extruded along Z = length):

  Male (wider at top):
        ___wt___
       /        \\
      /   wb     \\      h = height

  Female (narrow opening, wider inside):
    |←──── bw ─────→|
    |                |   bh = block_height
    |    wb          |
    |   /openng\\    |
    |  / groove  \\  |   h  = groove depth
    |/____wt______\\ |

Easy:   bare profile extrude
Medium: + chamfer on lips + mounting holes
Hard:   + oil groove along length
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ["male", "female"]


class DovetailSlideFamily(BaseFamily):
    name = "dovetail_slide"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(VARIANTS)
        width_top = rng.uniform(15, 55)  # male: wide end; female: groove wide end
        angle_deg = rng.uniform(45, 65)  # dovetail flank angle [°]
        # cap height so width_bottom >= width_top * 0.30 (avoid wedge shapes)
        max_h = (width_top * 0.70) / (2 * math.tan(math.radians(angle_deg)))
        height = rng.uniform(8, max(8.1, min(22, max_h)))
        length = rng.uniform(50, 200)  # extrude length
        taper = 2 * height * math.tan(math.radians(angle_deg))
        width_bot = round(width_top - taper, 2)

        params = {
            "variant": variant,
            "width_top": round(width_top, 1),  # wide end of dovetail
            "width_bottom": max(3.0, round(width_bot, 1)),  # narrow end
            "height": round(height, 1),
            "length": round(length, 1),
            "angle_deg": round(angle_deg, 1),
            "difficulty": difficulty,
        }

        if variant == "female":
            # Block dimensions: wall on each side + base below groove
            wall_t = round(width_top * rng.uniform(0.25, 0.45), 1)
            base_t = round(height * rng.uniform(0.30, 0.60), 1)
            params["block_width"] = round(width_top + 2 * wall_t, 1)
            params["block_height"] = round(height + base_t, 1)

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(
                rng.uniform(0.5, max(0.6, min(2.0, height * 0.10))), 1
            )
            n_holes = int(rng.choice([2, 3, 4]))
            if variant == "male":
                # cbore_d = hd*1.8 must fit in narrow face (wb) → hd < wb/1.8
                max_hd = params["width_bottom"] / 1.8 * 0.80
                if max_hd < 2.5:
                    n_holes = None  # face too narrow for any cbore
                else:
                    hole_d = rng.uniform(2.5, min(8, max_hd))
            else:
                hole_d = rng.uniform(3, min(8, max(3.1, params["block_width"] * 0.12)))
            if n_holes is not None:
                params["n_holes"] = n_holes
                params["hole_diameter"] = round(hole_d, 1)

        if difficulty == "hard":
            groove_w = round(rng.uniform(1.5, max(1.6, min(4.0, width_top * 0.08))), 1)
            groove_d = round(rng.uniform(0.5, max(0.6, min(1.5, height * 0.08))), 1)
            params["oil_groove_width"] = groove_w
            params["oil_groove_depth"] = groove_d

        return params

    def validate_params(self, params: dict) -> bool:
        wt = params["width_top"]
        wb = params["width_bottom"]
        h = params["height"]
        L = params["length"]
        variant = params.get("variant", "male")

        if wb < 2 or wt <= wb or h < 4 or L < 20:
            return False
        # reject extreme taper (wedge-like)
        if wb < max(2.0, wt * 0.15):
            return False

        if variant == "female":
            bw = params.get("block_width", 0)
            bh = params.get("block_height", 0)
            if bw <= wt + 2 or bh <= h + 1:
                return False

        hd = params.get("hole_diameter")
        if hd and hd >= h * 0.9:
            return False
        # cbore (1.8× hole_d) must fit within narrow face (wb) for male
        if hd and variant == "male" and hd * 1.8 > wb * 0.85:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "male")
        wt = params["width_top"]
        wb = params["width_bottom"]
        h = params["height"]
        L = params["length"]

        hw_t = round(wt / 2, 3)
        hw_b = round(wb / 2, 3)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # ── 1. Base solid ────────────────────────────────────────────────────

        if variant == "male":
            # Symmetric trapezoid: wide at base (y=0), narrow at sliding face (y=h)
            # Matches female groove: narrow opening at top, wide bottom
            pts = [
                (-hw_t, 0.0),
                (hw_t, 0.0),
                (hw_b, round(h, 3)),
                (-hw_b, round(h, 3)),
            ]
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("extrude", {"distance": round(L, 3)}))

        else:  # female
            bw = params["block_width"]
            bh = params["block_height"]
            hw_bw = round(bw / 2, 3)
            # Single polyline: outer block contour + dovetail groove notch at top.
            # Groove: narrow opening (wb) at y=bh, wide bottom (wt) at y=bh-h.
            pts = [
                (-hw_bw, 0.0),  # bottom-left
                (hw_bw, 0.0),  # bottom-right
                (hw_bw, round(bh, 3)),  # top-right (block corner)
                (hw_b, round(bh, 3)),  # groove opening right edge (narrow)
                (hw_t, round(bh - h, 3)),  # groove bottom right (wide)
                (-hw_t, round(bh - h, 3)),  # groove bottom left
                (-hw_b, round(bh, 3)),  # groove opening left edge
                (-hw_bw, round(bh, 3)),  # top-left (block corner)
            ]
            ops.append(Op("polyline", {"points": pts}))
            ops.append(Op("close", {}))
            ops.append(Op("extrude", {"distance": round(L, 3)}))

        # ── 2. Chamfer on dovetail lips (medium+) ────────────────────────────
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            if variant == "male":
                # Chamfer the two top-face long edges
                ops.append(Op("faces", {"selector": ">Y"}))
                ops.append(Op("chamfer", {"length": cl}))
            else:
                # Chamfer the groove opening edges on top face
                ops.append(Op("faces", {"selector": ">Y"}))
                ops.append(Op("chamfer", {"length": cl}))

        # ── 3. Mounting holes (medium+) ──────────────────────────────────────
        n_h = params.get("n_holes")
        hd = params.get("hole_diameter")
        if n_h and hd:
            tags["has_hole"] = True
            spacing = round(L / (n_h + 1), 3)
            hole_pts = [(0.0, round(-L / 2 + spacing * (i + 1), 3)) for i in range(n_h)]
            cbore_d = round(hd * 1.8, 1)
            cbore_dep = round(h * 0.4, 2)
            if variant == "male":
                # Holes on base face (<Y = wide face) — cbore fits comfortably in wide base
                ops.append(Op("workplane", {"selector": "<Y"}))
            else:
                # Holes on bottom face (<Y) for mounting the guide body
                ops.append(Op("workplane", {"selector": "<Y"}))
            ops.append(Op("pushPoints", {"points": hole_pts}))
            ops.append(
                Op(
                    "cboreHole",
                    {
                        "diameter": hd,
                        "cboreDiameter": cbore_d,
                        "cboreDepth": cbore_dep,
                    },
                )
            )

        # ── 4. Oil groove along length (hard) ────────────────────────────────
        gw = params.get("oil_groove_width")
        gd = params.get("oil_groove_depth")
        if gw and gd:
            tags["has_slot"] = True
            if variant == "male":
                # Longitudinal slot on top face
                ops.append(Op("workplane", {"selector": ">Y"}))
                ops.append(Op("center", {"x": 0.0, "y": 0.0}))
                ops.append(Op("rect", {"length": gw, "width": round(L * 0.8, 2)}))
                ops.append(Op("cutBlind", {"depth": gd}))
            else:
                # Oil groove on the groove bottom surface (inside the slot)
                # Use explicit world-coord cut: centered on the groove bottom
                bh = params["block_height"]
                groove_bottom_y = round(bh - h, 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [
                                            0,
                                            round(groove_bottom_y - gd / 2, 3),
                                            0,
                                        ],
                                        "rotate": [90, 0, 0],
                                    },
                                },
                                {
                                    "name": "rect",
                                    "args": {
                                        "length": gw,
                                        "width": round(L * 0.8, 2),
                                    },
                                },
                                {
                                    "name": "extrude",
                                    "args": {"distance": round(gd * 2, 3)},
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
