"""Locator block with V-groove — fixture/jig reference block.

Typical use: workholding datum block, V-block for round stock, CMM fixture.
Easy:   rectangular block + V-groove + 2 mounting holes
Medium: + pin holes (sides) + chamfer
Hard:   + threaded boss pocket + fillet
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class LocatorBlockFamily(BaseFamily):
    name = "locator_block"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        length = rng.uniform(40, 150)
        width = rng.uniform(30, 100)
        height = rng.uniform(20, 80)

        # V-groove: depth and half-angle determine width at top
        v_depth = rng.uniform(height * 0.2, height * 0.5)
        v_angle_deg = rng.uniform(30, 60)  # half-angle
        import math

        v_width_top = 2 * v_depth * math.tan(math.radians(v_angle_deg))

        inset = rng.uniform(6, max(7, min(20, length / 6, width / 5)))
        hole_d = rng.uniform(3.0, min(8.0, inset * 0.6))

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "v_depth": round(v_depth, 1),
            "v_width_top": round(v_width_top, 1),
            "mount_inset": round(inset, 1),
            "mount_hole_diameter": round(hole_d, 1),
            "difficulty": difficulty,
        }

        # Spread features cross-difficulty (was strict by diff)
        pin_prob = {"easy": 0.2, "medium": 0.7, "hard": 0.85}[difficulty]
        chamfer_prob = {"easy": 0.3, "medium": 0.7, "hard": 0.85}[difficulty]
        boss_prob = {"easy": 0.0, "medium": 0.3, "hard": 0.7}[difficulty]
        fillet_prob = {"easy": 0.2, "medium": 0.5, "hard": 0.7}[difficulty]

        if rng.random() < pin_prob:
            pin_d = rng.uniform(3.0, min(8.0, width * 0.12))
            params["pin_diameter"] = round(pin_d, 1)
            params["pin_depth"] = round(
                rng.uniform(pin_d * 1.5, min(20.0, width * 0.35)), 1
            )
        if rng.random() < chamfer_prob:
            params["chamfer_length"] = round(rng.uniform(0.5, min(2.0, height / 12)), 1)
            params["chamfer_op"] = str(rng.choice(["chamfer", "fillet"]))
        if rng.random() < boss_prob:
            boss_d = rng.uniform(8, min(20, width * 0.3))
            boss_depth = rng.uniform(3.0, min(10.0, height * 0.2))
            params["boss_pocket_diameter"] = round(boss_d, 1)
            params["boss_pocket_depth"] = round(boss_depth, 1)
        if rng.random() < fillet_prob:
            params["fillet_radius"] = round(rng.uniform(0.5, min(2.0, height / 15)), 1)
        # Code-syntax: mount hole pushPoints order
        params["hole_order_swap"] = bool(rng.random() < 0.5)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w, h = params["length"], params["width"], params["height"]
        vd = params["v_depth"]
        vwt = params["v_width_top"]
        ins = params["mount_inset"]
        hd = params["mount_hole_diameter"]

        if vd >= h * 0.6 or vd < 4:
            return False
        if vwt >= w - 4 or vwt < 4:
            return False
        if ins < 5 or hd >= ins * 0.8:
            return False
        if ins + hd / 2 > min(l, w) / 2 - 2:
            return False

        pin_d = params.get("pin_diameter")
        pin_depth = params.get("pin_depth")
        if pin_d and pin_depth:
            if pin_d >= w * 0.2 or pin_depth >= l / 2 - 4:
                return False

        bp_d = params.get("boss_pocket_diameter")
        bp_depth = params.get("boss_pocket_depth")
        if bp_d and bp_depth:
            if bp_d >= w * 0.4 or bp_depth >= h * 0.3:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w, h = params["length"], params["width"], params["height"]
        vd = params["v_depth"]
        vwt = params["v_width_top"]
        ins = params["mount_inset"]
        hd = params["mount_hole_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # Base block
        ops.append(Op("box", {"length": l, "width": w, "height": h}))

        # Edge fillet/chamfer top — BEFORE V-groove (推 fillet/chamfer 频率)
        cl = params.get("chamfer_length")
        chamfer_op = params.get("chamfer_op", "chamfer")
        if cl:
            if chamfer_op == "fillet":
                tags["has_fillet"] = True
            else:
                tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            if chamfer_op == "fillet":
                ops.append(Op("fillet", {"radius": cl}))
            else:
                ops.append(Op("chamfer", {"length": cl}))

        # V-groove cut: rectangular slot of width vwt and depth vd from top face
        half_vw = round(vwt / 2, 3)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("center", {"x": 0.0, "y": 0.0}))
        ops.append(Op("rect", {"length": vwt, "width": round(l + 2, 3)}))
        ops.append(Op("cutBlind", {"depth": round(vd, 3)}))

        # Mounting holes (bottom face)
        ops.append(Op("workplane", {"selector": "<Z"}))
        pts = [
            (round(l / 2 - ins, 3), round(w / 2 - ins, 3)),
            (round(-l / 2 + ins, 3), round(w / 2 - ins, 3)),
            (round(l / 2 - ins, 3), round(-w / 2 + ins, 3)),
            (round(-l / 2 + ins, 3), round(-w / 2 + ins, 3)),
        ]
        if params.get("hole_order_swap", False):
            pts = list(reversed(pts))
        ops.append(Op("pushPoints", {"points": pts}))
        ops.append(Op("hole", {"diameter": hd}))

        # Pin holes from side face (medium+)
        pin_d = params.get("pin_diameter")
        pin_depth = params.get("pin_depth")
        if pin_d and pin_depth:
            # pin from >Y face, centered in Z
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(
                Op(
                    "pushPoints",
                    {
                        "points": [
                            (round(l / 4, 3), round(h / 2 - ins, 3)),
                            (round(-l / 4, 3), round(h / 2 - ins, 3)),
                        ]
                    },
                )
            )
            ops.append(Op("hole", {"diameter": pin_d, "depth": pin_depth}))

        # Boss pocket (hard)
        bp_d = params.get("boss_pocket_diameter")
        bp_depth = params.get("boss_pocket_depth")
        if bp_d and bp_depth:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": "<Y"}))
            ops.append(Op("circle", {"radius": bp_d / 2}))
            ops.append(Op("cutBlind", {"depth": bp_depth}))

        # Chamfer already applied above (before V-groove)

        # Fillet (hard)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
