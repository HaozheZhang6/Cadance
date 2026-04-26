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

        # Spread features cross-difficulty
        hole_prob = {"easy": 0.3, "medium": 0.7, "hard": 0.85}[difficulty]
        slot_prob = {"easy": 0.0, "medium": 0.3, "hard": 0.75}[difficulty]
        edge_prob = {"easy": 0.3, "medium": 0.55, "hard": 0.7}[difficulty]

        if rng.random() < hole_prob:
            hole_d = max(3.0, round(min(rail * 0.5, 8.0), 1))
            params["hole_diameter"] = hole_d
            params["bore_form"] = str(rng.choice(["hole", "cut"]))

        if rng.random() < slot_prob:
            slot_d = max(3.0, round(min(rail * 0.40, 7.0), 1))
            params["side_slot_depth"] = slot_d

        # Edge fillet/chamfer on inner window or outer perimeter (推 fillet 频率)
        if rng.random() < edge_prob:
            params["edge_op"] = str(rng.choice(["fillet", "chamfer"]))
            params["edge_size"] = round(min(thick * 0.3, rail * 0.2, 1.5), 2)
            params["edge_loc"] = str(rng.choice(["top", "bottom", "both"]))

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
        if sd and sd >= rail * 0.55:
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
            bore_form = params.get("bore_form", "hole")
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": corner_pts}))
            if bore_form == "hole":
                ops.append(Op("hole", {"diameter": round(hd, 4)}))
            else:
                ops.append(Op("circle", {"radius": round(hd / 2, 4)}))
                ops.append(Op("cutThruAll", {}))

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

        # Edge fillet/chamfer (推 fillet 频率)
        edge_op = params.get("edge_op")
        edge_size = float(params.get("edge_size", 0.0))
        edge_loc = params.get("edge_loc", "top")
        if edge_op and edge_size > 0:
            if edge_op == "fillet":
                tags["has_fillet"] = True
            else:
                tags["has_chamfer"] = True
            sels = {"top": [">Z"], "bottom": ["<Z"], "both": [">Z", "<Z"]}[edge_loc]
            for sel in sels:
                ops.append(Op("faces", {"selector": sel}))
                ops.append(Op("edges", {}))
                if edge_op == "fillet":
                    ops.append(Op("fillet", {"radius": edge_size}))
                else:
                    ops.append(Op("chamfer", {"length": edge_size}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
