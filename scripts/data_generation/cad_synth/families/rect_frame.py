"""Frame plate — rectangular frame (outer rect minus inner rect) wire-EDM plate.

A flat rectangular frame: outer rectangle with a rectangular window cut through.
Common as shims, gaskets, panel frames, spacer frames.

Easy:   plain rectangular frame.
Medium: + rounded inner corners (arcs) + corner mounting holes.
Hard:   + side slot cutouts on outer edges.
"""


from ..pipeline.builder import Op, Program
from .base import BaseFamily


class RectFrameFamily(BaseFamily):
    name = "rect_frame"

    def sample_params(self, difficulty: str, rng) -> dict:
        outer_l = round(rng.uniform(60, 160), 1)
        outer_w = round(rng.uniform(40, 120), 1)
        rail = round(rng.uniform(8, 30), 1)  # frame rail width
        thick = round(rng.uniform(3, 12), 1)

        params = {
            "outer_length": outer_l,
            "outer_width": outer_w,
            "rail_width": rail,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            corner_r = round(rng.uniform(3, max(3.5, min(rail * 0.5, 10))), 1)
            hole_d = round(rng.uniform(3, max(3.5, min(rail * 0.55, 8))), 1)
            params["corner_radius"] = corner_r
            params["hole_diameter"] = hole_d

        if difficulty == "hard":
            slot_d = round(rng.uniform(4, max(4.5, min(rail * 0.6, 10))), 1)
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

        cr = params.get("corner_radius", 0)
        if cr and cr >= rail * 0.6:
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

        # Corner mounting holes + rounded inner corners effect via holes at inner corners (medium+)
        hd = params.get("hole_diameter")
        cr = params.get("corner_radius")
        if hd and cr:
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
