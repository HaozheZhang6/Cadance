"""Frame plate — rectangular frame (outer rect minus inner rect) wire-EDM plate.

A flat rectangular frame: outer rectangle with a rectangular window cut through.
Common as shims, gaskets, panel frames, spacer frames.
No governing standard (custom machined / wire-EDM part); proportions follow
typical fabrication practice: rail 10–20 % of outer dim, thick 3–12 mm.

Easy:   plain rectangular frame.
Medium: + corner mounting holes.
Hard:   + side slot cutouts on outer edges.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# Preferred outer dimensions (mm) — common machined frame sizes
_OUTER_L = [60, 80, 100, 120, 150, 200, 250, 300]
_OUTER_W = [40, 50, 60, 80, 100, 120, 150, 200]
_RAIL_FRAC = [0.10, 0.12, 0.15, 0.18, 0.20]  # rail / outer_min
_THICK_MM = [3, 4, 5, 6, 8, 10, 12]


class RectFrameFamily(BaseFamily):
    name = "rect_frame"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        ol_pool = _OUTER_L[:5] if difficulty == "easy" else _OUTER_L
        ow_pool = _OUTER_W[:5] if difficulty == "easy" else _OUTER_W
        outer_l = float(ol_pool[int(rng.integers(0, len(ol_pool)))])
        outer_w = float(ow_pool[int(rng.integers(0, len(ow_pool)))])
        frac = float(rng.choice(_RAIL_FRAC))
        rail = round(min(outer_l, outer_w) * frac, 1)
        thick = float(_THICK_MM[int(rng.integers(0, len(_THICK_MM)))])

        params = {
            "outer_length": outer_l,
            "outer_width": outer_w,
            "rail_width": rail,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            hole_d = round(min(rail * 0.5, 8.0), 1)
            hole_d = max(3.0, hole_d)
            params["hole_diameter"] = hole_d

        if difficulty == "hard":
            slot_d = round(min(rail * 0.55, 10.0), 1)
            slot_d = max(4.0, slot_d)
            params["side_slot_depth"] = slot_d

        return params

    def validate_params(self, params: dict) -> bool:
        ol = params["outer_length"]
        ow = params["outer_width"]
        rail = params["rail_width"]
        thick = params["thickness"]

        inner_l = ol - 2 * rail
        inner_w = ow - 2 * rail

        if inner_l < 10:
            return False
        if inner_w < 10:
            return False
        if rail < 6:
            return False
        if thick < 2:
            return False

        hd = params.get("hole_diameter", 0)
        if hd and hd >= rail * 0.65:
            return False

        sd = params.get("side_slot_depth", 0)
        if sd and sd >= rail * 0.7:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ol = params["outer_length"]
        ow = params["outer_width"]
        rail = params["rail_width"]
        thick = params["thickness"]

        inner_l = round(ol - 2 * rail, 4)
        inner_w = round(ow - 2 * rail, 4)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Outer rectangle extrude
        ops.append(Op("rect", {"length": round(ol, 4), "width": round(ow, 4)}))
        ops.append(Op("extrude", {"distance": round(thick, 4)}))

        # Inner window cut
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rect", {"length": inner_l, "width": inner_w}))
        ops.append(Op("cutThruAll", {}))

        # Corner mounting holes (medium+)
        hd = params.get("hole_diameter")
        if hd:
            tags["has_hole"] = True
            # Mounting holes at outer corners (inset by rail/2)
            half_ol = round(ol / 2 - rail / 2, 4)
            half_ow = round(ow / 2 - rail / 2, 4)
            corner_pts = [
                (half_ol, half_ow),
                (-half_ol, half_ow),
                (half_ol, -half_ow),
                (-half_ol, -half_ow),
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": corner_pts}))
            ops.append(Op("hole", {"diameter": round(hd, 4)}))

        # Side slot cutouts on long edges (hard)
        sd = params.get("side_slot_depth")
        if sd:
            slot_len = round(ol * 0.25, 4)
            half_ow = round(ow / 2, 4)
            for sign in [1, -1]:
                cy = round(sign * half_ow, 4)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0.0, cy, 0.0],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": round(slot_len, 4),
                                        "width": round(sd, 4),
                                        "height": round(thick + 1, 4),
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
