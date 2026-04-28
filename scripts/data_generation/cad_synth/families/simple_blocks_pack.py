"""simple_blocks_pack — 15 box-primitive + cut/feature families.

Reference: F360 sample inspection + general mechanical design vocabulary.
All families start with a box primitive and add cuts, holes, slots, or
feature edges — exercising hole/slot2D/cutThruAll/cutBlind/chamfer/fillet ops.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


# 1. simple_block_chamfered — basic box + chamfer all 12 edges
class SimpleBlockChamferedFamily(BaseFamily):
    name = "simple_block_chamfered"
    standard = "N/A"
    REF = "imagined: machined mounting block"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(30, 80)), 1),
            "width": round(float(rng.uniform(20, 60)), 1),
            "height": round(float(rng.uniform(15, 40)), 1),
            "chamfer": round(float(rng.uniform(0.5, 2.5)), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return all(p[k] > p["chamfer"] * 4 for k in ("length", "width", "height"))

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("edges", {}),
            Op("chamfer", {"length": p["chamfer"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_chamfer": True, "ref": self.REF},
        )


# 2. simple_block_filleted — basic box + fillet all edges (rounded brick)
class SimpleBlockFilletedFamily(BaseFamily):
    name = "simple_block_filleted"
    standard = "N/A"
    REF = "imagined: rounded box / soap bar"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(40, 80)), 1),
            "width": round(float(rng.uniform(25, 60)), 1),
            "height": round(float(rng.uniform(20, 40)), 1),
            "fillet": round(float(rng.uniform(2, 6)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return all(p[k] > p["fillet"] * 2 + 4 for k in ("length", "width", "height"))

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("edges", {}),
            Op("fillet", {"radius": p["fillet"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_fillet": True, "ref": self.REF},
        )


# 3. simple_pyramid_block — frustum pyramid (base square shrinks at top)
class SimplePyramidBlockFamily(BaseFamily):
    name = "simple_pyramid_block"
    standard = "N/A"
    REF = "imagined: pedestal / foundation block"

    def sample_params(self, difficulty, rng):
        bw = round(float(rng.uniform(40, 80)), 1)
        return {
            "base_l": bw,
            "base_w": round(bw * float(rng.uniform(0.7, 1.0)), 1),
            "top_l": round(bw * float(rng.uniform(0.4, 0.8)), 1),
            "top_w": round(bw * float(rng.uniform(0.3, 0.6)), 1),
            "height": round(bw * float(rng.uniform(0.4, 0.8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["top_l"] < p["base_l"] and p["top_w"] < p["base_w"] and p["height"] >= 8
        )

    def make_program(self, p):
        ops = [
            Op("rect", {"length": p["base_l"], "width": p["base_w"]}),
            Op("transformed", {"offset": [0, 0, p["height"]], "rotate": [0, 0, 0]}),
            Op("rect", {"length": p["top_l"], "width": p["top_w"]}),
            Op("loft", {"combine": True}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"loft": True, "ref": self.REF},
        )


# 4. simple_obelisk — tall narrow truncated pyramid
class SimpleObeliskFamily(BaseFamily):
    name = "simple_obelisk"
    standard = "N/A"
    REF = "imagined: obelisk monument"

    def sample_params(self, difficulty, rng):
        bw = round(float(rng.uniform(15, 30)), 1)
        return {
            "base_w": bw,
            "top_w": round(bw * float(rng.uniform(0.3, 0.6)), 1),
            "height": round(bw * float(rng.uniform(2.5, 4.5)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["top_w"] < p["base_w"] - 2 and p["height"] >= 30

    def make_program(self, p):
        ops = [
            Op("rect", {"length": p["base_w"], "width": p["base_w"]}),
            Op("transformed", {"offset": [0, 0, p["height"]], "rotate": [0, 0, 0]}),
            Op("rect", {"length": p["top_w"], "width": p["top_w"]}),
            Op("loft", {"combine": True}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"loft": True, "ref": self.REF},
        )


# 5. simple_block_with_pocket — box + rect cavity
class SimpleBlockWithPocketFamily(BaseFamily):
    name = "simple_block_with_pocket"
    standard = "N/A"
    REF = "imagined: housing with rectangular cavity"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(40, 90)), 1)
        W = round(float(rng.uniform(30, 70)), 1)
        H = round(float(rng.uniform(15, 35)), 1)
        return {
            "length": L,
            "width": W,
            "height": H,
            "pocket_l": round(L * float(rng.uniform(0.4, 0.75)), 1),
            "pocket_w": round(W * float(rng.uniform(0.4, 0.75)), 1),
            "pocket_d": round(H * float(rng.uniform(0.3, 0.7)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["pocket_l"] < p["length"] - 8
            and p["pocket_w"] < p["width"] - 8
            and p["pocket_d"] < p["height"] - 3
        )

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("rect", {"length": p["pocket_l"], "width": p["pocket_w"]}),
            Op("cutBlind", {"depth": p["pocket_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_pocket": True, "ref": self.REF},
        )


# 6. simple_block_with_through_slot — box + rect slot all the way through
class SimpleBlockWithThroughSlotFamily(BaseFamily):
    name = "simple_block_with_through_slot"
    standard = "N/A"
    REF = "imagined: yoke / slotted-bracket"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(40, 90)), 1)
        return {
            "length": L,
            "width": round(float(rng.uniform(30, 70)), 1),
            "height": round(float(rng.uniform(15, 35)), 1),
            "slot_l": round(L * float(rng.uniform(0.4, 0.7)), 1),
            "slot_w": round(float(rng.uniform(4, 12)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["slot_l"] < p["length"] - 10
            and p["slot_w"] < p["width"] - 10
            and p["height"] >= 6
        )

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("slot2D", {"length": p["slot_l"], "width": p["slot_w"]}),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_slot": True, "ref": self.REF},
        )


# 7. simple_block_with_round_hole — box + 1 through round hole
class SimpleBlockWithRoundHoleFamily(BaseFamily):
    name = "simple_block_with_round_hole"
    standard = "N/A"
    REF = "imagined: simple bushing block"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(30, 70)), 1),
            "width": round(float(rng.uniform(30, 70)), 1),
            "height": round(float(rng.uniform(15, 40)), 1),
            "hole_d": round(float(rng.uniform(5, 15)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["hole_d"] < min(p["length"], p["width"]) - 6

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["hole_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_hole": True, "ref": self.REF},
        )


# 8. simple_block_with_oval_hole — box + 1 through slot2D
class SimpleBlockWithOvalHoleFamily(BaseFamily):
    name = "simple_block_with_oval_hole"
    standard = "N/A"
    REF = "imagined: adjustable mounting bracket"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(40, 80)), 1)
        return {
            "length": L,
            "width": round(float(rng.uniform(30, 70)), 1),
            "height": round(float(rng.uniform(8, 20)), 1),
            "slot_l": round(L * float(rng.uniform(0.3, 0.55)), 1),
            "slot_w": round(float(rng.uniform(5, 12)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["slot_w"] + 8 < p["width"] and p["slot_l"] + 10 < p["length"]

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("slot2D", {"length": p["slot_l"], "width": p["slot_w"]}),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_slot": True, "ref": self.REF},
        )


# 9. simple_block_with_keyway — box + DIN-style keyway slot
class SimpleBlockWithKeywayFamily(BaseFamily):
    name = "simple_block_with_keyway"
    standard = "N/A"
    REF = "imagined: keyed motor mount"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(40, 80)), 1),
            "width": round(float(rng.uniform(30, 60)), 1),
            "height": round(float(rng.uniform(20, 40)), 1),
            "keyway_w": round(float(rng.uniform(4, 9)), 1),
            "keyway_d": round(float(rng.uniform(4, 9)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["keyway_w"] < p["width"] - 6 and p["keyway_d"] < p["height"] - 4

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": 0, "y": -(p["width"] / 2)}),
            Op("rect", {"length": p["keyway_w"], "width": p["keyway_d"] * 2}),
            Op("cutBlind", {"depth": p["keyway_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_keyway": True, "ref": self.REF},
        )


# 10. simple_block_with_cross_cut — box + plus-shape cut
class SimpleBlockWithCrossCutFamily(BaseFamily):
    name = "simple_block_with_cross_cut"
    standard = "N/A"
    REF = "imagined: phillips head receiver"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(50, 90)), 1)
        W = round(float(rng.uniform(50, 90)), 1)
        return {
            "length": L,
            "width": W,
            "height": round(float(rng.uniform(15, 35)), 1),
            "cross_arm": round(min(L, W) * float(rng.uniform(0.25, 0.45)), 1),
            "cross_t": round(float(rng.uniform(4, 10)), 1),
            "depth": round(float(rng.uniform(4, 10)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["cross_arm"] * 2 + 8 < min(p["length"], p["width"])
            and p["depth"] < p["height"] - 2
        )

    def make_program(self, p):
        a = p["cross_arm"]
        t = p["cross_t"]
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("rect", {"length": a * 2, "width": t}),
            Op("cutBlind", {"depth": p["depth"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("rect", {"length": t, "width": a * 2}),
            Op("cutBlind", {"depth": p["depth"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_cross": True, "ref": self.REF},
        )


# 11. simple_block_with_array_holes — box + 3×3 hole grid
class SimpleBlockWithArrayHolesFamily(BaseFamily):
    name = "simple_block_with_array_holes"
    standard = "N/A"
    REF = "imagined: perforated mounting brick"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(50, 100)), 1),
            "width": round(float(rng.uniform(40, 80)), 1),
            "height": round(float(rng.uniform(15, 30)), 1),
            "n_x": int(rng.choice([2, 3, 4])),
            "n_y": int(rng.choice([2, 3, 4])),
            "hole_d": round(float(rng.uniform(3, 8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["hole_d"] * (p["n_x"] + 1) < p["length"]
            and p["hole_d"] * (p["n_y"] + 1) < p["width"]
        )

    def make_program(self, p):
        sx = p["length"] / (p["n_x"] + 1)
        sy = p["width"] / (p["n_y"] + 1)
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "rarray",
                {
                    "xSpacing": sx,
                    "ySpacing": sy,
                    "xCount": p["n_x"],
                    "yCount": p["n_y"],
                },
            ),
            Op("hole", {"diameter": p["hole_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rarray": (p["n_x"], p["n_y"]), "ref": self.REF},
        )


# 12. simple_block_with_chamfered_corners — box + chamfer top edges only
class SimpleBlockWithChamferedCornersFamily(BaseFamily):
    name = "simple_block_with_chamfered_corners"
    standard = "N/A"
    REF = "imagined: machined block with finished top"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(40, 80)), 1),
            "width": round(float(rng.uniform(30, 60)), 1),
            "height": round(float(rng.uniform(15, 35)), 1),
            "chamfer": round(float(rng.uniform(1, 4)), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return min(p["length"], p["width"], p["height"]) > p["chamfer"] * 4

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("edges", {"selector": ">Z"}),
            Op("chamfer", {"length": p["chamfer"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_chamfer": True, "ref": self.REF},
        )


# 13. simple_dovetail_block — block with trapezoidal slot (tail joint)
class SimpleDovetailBlockFamily(BaseFamily):
    name = "simple_dovetail_block"
    standard = "N/A"
    REF = "imagined: dovetail joint slide block"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(50, 100)), 1)
        W = round(float(rng.uniform(40, 70)), 1)
        H = round(float(rng.uniform(20, 35)), 1)
        # Top width smaller, bottom width larger; clamp by W to keep valid
        top_w = round(float(rng.uniform(6, 14)), 1)
        bot_w = round(min(top_w + float(rng.uniform(5, 12)), W * 0.7), 1)
        return {
            "length": L,
            "width": W,
            "height": H,
            "slot_top_w": top_w,
            "slot_bot_w": bot_w,
            "slot_d": round(float(rng.uniform(6, 14)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["slot_bot_w"] > p["slot_top_w"] + 2
            and p["slot_bot_w"] < p["width"] - 4
            and p["slot_d"] < p["height"] - 4
        )

    def make_program(self, p):
        # Build trapezoidal cutter via polyline + extrude, then cut
        L = p["length"]
        H = p["height"]
        D = p["slot_d"]
        top_w = p["slot_top_w"]
        bot_w = p["slot_bot_w"]
        ops = [
            Op(
                "box", {"length": L, "width": p["width"], "height": H, "centered": True}
            ),
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "moveTo", "args": {"x": -top_w / 2, "y": -L / 2}},
                        {"name": "lineTo", "args": {"x": top_w / 2, "y": -L / 2}},
                        {"name": "lineTo", "args": {"x": top_w / 2, "y": L / 2}},
                        {"name": "lineTo", "args": {"x": -top_w / 2, "y": L / 2}},
                        {"name": "close", "args": {}},
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, H / 2 - D], "rotate": [0, 0, 0]},
                        },
                        {"name": "moveTo", "args": {"x": -bot_w / 2, "y": -L / 2}},
                        {"name": "lineTo", "args": {"x": bot_w / 2, "y": -L / 2}},
                        {"name": "lineTo", "args": {"x": bot_w / 2, "y": L / 2}},
                        {"name": "lineTo", "args": {"x": -bot_w / 2, "y": L / 2}},
                        {"name": "close", "args": {}},
                        {"name": "loft", "args": {"combine": True}},
                    ],
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_dovetail": True, "ref": self.REF},
        )


# 14. simple_v_block — block with V-groove cut
class SimpleVBlockFamily(BaseFamily):
    name = "simple_v_block"
    standard = "N/A"
    REF = "imagined: V-block jig fixture"

    def sample_params(self, difficulty, rng):
        W = round(float(rng.uniform(40, 60)), 1)
        H = round(float(rng.uniform(25, 40)), 1)
        return {
            "length": round(float(rng.uniform(40, 90)), 1),
            "width": W,
            "height": H,
            "v_top_w": round(W * float(rng.uniform(0.35, 0.65)), 1),
            "v_depth": round(H * float(rng.uniform(0.3, 0.55)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["v_top_w"] < p["width"] - 6 and p["v_depth"] < p["height"] - 4

    def make_program(self, p):
        # Cut a V-shape groove along the length axis (Y direction)
        L = p["length"]
        W = p["width"]
        H = p["height"]
        ops = [
            Op("box", {"length": L, "width": W, "height": H, "centered": True}),
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        # V-shape outline in the YZ cross section, extruded along X
                        {
                            "name": "moveTo",
                            "args": {"x": -p["v_top_w"] / 2, "y": H / 2},
                        },
                        {"name": "lineTo", "args": {"x": p["v_top_w"] / 2, "y": H / 2}},
                        {
                            "name": "lineTo",
                            "args": {"x": 0.0, "y": H / 2 - p["v_depth"]},
                        },
                        {"name": "close", "args": {}},
                        {"name": "extrude", "args": {"distance": L, "both": True}},
                    ],
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_groove": True, "ref": self.REF},
        )


# 15. simple_block_with_round_pocket — box + round cylindrical cavity
class SimpleBlockWithRoundPocketFamily(BaseFamily):
    name = "simple_block_with_round_pocket"
    standard = "N/A"
    REF = "imagined: receiver block / cup holder"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(50, 80)), 1)
        W = round(float(rng.uniform(50, 80)), 1)
        H = round(float(rng.uniform(20, 40)), 1)
        return {
            "length": L,
            "width": W,
            "height": H,
            "pocket_r": round(min(L, W) * float(rng.uniform(0.18, 0.35)), 1),
            "pocket_depth": round(H * float(rng.uniform(0.3, 0.65)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["pocket_r"] * 2 + 8 < min(p["length"], p["width"])
            and p["pocket_depth"] < p["height"] - 4
        )

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["length"],
                    "width": p["width"],
                    "height": p["height"],
                    "centered": True,
                },
            ),
            Op("faces", {"selector": ">Z"}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["pocket_r"]}),
            Op("cutBlind", {"depth": p["pocket_depth"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_pocket": True, "ref": self.REF},
        )


ALL_FAMILIES = [
    SimpleBlockChamferedFamily,
    SimpleBlockFilletedFamily,
    SimplePyramidBlockFamily,
    SimpleObeliskFamily,
    SimpleBlockWithPocketFamily,
    SimpleBlockWithThroughSlotFamily,
    SimpleBlockWithRoundHoleFamily,
    SimpleBlockWithOvalHoleFamily,
    SimpleBlockWithKeywayFamily,
    SimpleBlockWithCrossCutFamily,
    SimpleBlockWithArrayHolesFamily,
    SimpleBlockWithChamferedCornersFamily,
    SimpleDovetailBlockFamily,
    SimpleVBlockFamily,
    SimpleBlockWithRoundPocketFamily,
]
