"""simple_multi_stage_pack — 12 multi-extrude / multi-stage families.

Reference: F360 multi-extrude designs (samples with 2-4 extrudes ~30%).
Each family demonstrates a recognizable mechanical pattern: hub on plate,
boss on disc, peg array on plate, etc.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


# 1. simple_disc_with_boss
class SimpleDiscWithBossFamily(BaseFamily):
    name = "simple_disc_with_boss"
    standard = "N/A"
    REF = "f360:multi-extrude common (disc + cyl boss)"

    def sample_params(self, difficulty, rng):
        rd = round(float(rng.uniform(20, 40)), 1)
        return {
            "disc_r": rd,
            "disc_h": round(float(rng.uniform(4, 10)), 1),
            "boss_r": round(rd * float(rng.uniform(0.3, 0.55)), 1),
            "boss_h": round(float(rng.uniform(8, 20)), 1),
            "with_bore": difficulty != "easy",
            "bore_d": round(rd * float(rng.uniform(0.1, 0.25)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["boss_r"] < p["disc_r"] - 2 and p["bore_d"] < p["boss_r"] * 1.6

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["disc_r"]}),
            Op("extrude", {"distance": p["disc_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["boss_r"]}),
            Op("extrude", {"distance": p["boss_h"]}),
        ]
        if p["with_bore"]:
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 2. simple_disc_with_pegs (disc + N small cylinders polar)
class SimpleDiscWithPegsFamily(BaseFamily):
    name = "simple_disc_with_pegs"
    standard = "N/A"
    REF = "imagined: index plate / lego baseplate"

    def sample_params(self, difficulty, rng):
        rd = round(float(rng.uniform(25, 45)), 1)
        return {
            "disc_r": rd,
            "disc_h": round(float(rng.uniform(3, 8)), 1),
            "n_pegs": int(rng.choice([4, 5, 6, 8])),
            "peg_r": round(float(rng.uniform(2, 4)), 1),
            "peg_h": round(float(rng.uniform(4, 10)), 1),
            "peg_pcd": round(rd * float(rng.uniform(0.55, 0.8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["peg_pcd"] + p["peg_r"] < p["disc_r"] - 2

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["disc_r"]}),
            Op("extrude", {"distance": p["disc_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": p["peg_pcd"],
                    "startAngle": 0,
                    "angle": 360,
                    "count": p["n_pegs"],
                },
            ),
            Op("circle", {"radius": p["peg_r"]}),
            Op("extrude", {"distance": p["peg_h"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"polar_array": p["n_pegs"], "ref": self.REF},
        )


# 3. simple_plate_with_pegs (rect plate + array pegs)
class SimplePlateWithPegsFamily(BaseFamily):
    name = "simple_plate_with_pegs"
    standard = "N/A"
    REF = "imagined: stud-up baseplate"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(50, 90)), 1),
            "width": round(float(rng.uniform(40, 70)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
            "n_x": int(rng.choice([2, 3, 4])),
            "n_y": int(rng.choice([2, 3, 4])),
            "peg_r": round(float(rng.uniform(2.5, 5)), 1),
            "peg_h": round(float(rng.uniform(4, 10)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        sx = p["length"] / (p["n_x"] + 1)
        sy = p["width"] / (p["n_y"] + 1)
        return p["peg_r"] * 2 + 1 < min(sx, sy)

    def make_program(self, p):
        sx = p["length"] / (p["n_x"] + 1)
        sy = p["width"] / (p["n_y"] + 1)
        ops = [
            Op("rect", {"length": p["length"], "width": p["width"]}),
            Op("extrude", {"distance": p["thickness"]}),
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
            Op("circle", {"radius": p["peg_r"]}),
            Op("extrude", {"distance": p["peg_h"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rarray": (p["n_x"], p["n_y"]), "ref": self.REF},
        )


# 4. simple_disc_with_skirt (disc + outer flange ring)
class SimpleDiscWithSkirtFamily(BaseFamily):
    name = "simple_disc_with_skirt"
    standard = "N/A"
    REF = "imagined: cup / pot lid with rim"

    def sample_params(self, difficulty, rng):
        rd = round(float(rng.uniform(25, 50)), 1)
        return {
            "disc_r": rd,
            "skirt_r": round(rd * float(rng.uniform(1.1, 1.35)), 1),
            "disc_h": round(float(rng.uniform(4, 10)), 1),
            "skirt_h": round(float(rng.uniform(6, 18)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["skirt_r"] > p["disc_r"] + 2 and p["skirt_h"] > p["disc_h"]

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["skirt_r"]}),
            Op("circle", {"radius": p["disc_r"]}),
            Op("extrude", {"distance": p["skirt_h"]}),
            Op("workplane", {"selector": "<Z"}),
            Op("circle", {"radius": p["disc_r"]}),
            Op("extrude", {"distance": p["disc_h"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 5. simple_button — disc + dome top (sphere intersect)
class SimpleButtonFamily(BaseFamily):
    name = "simple_button"
    standard = "N/A"
    REF = "imagined: button / arcade switch cap"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(15, 30)), 1)
        return {
            "radius": r,
            "base_h": round(float(rng.uniform(3, 8)), 1),
            "dome_r": round(r * float(rng.uniform(1.0, 1.4)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["dome_r"] >= p["radius"] and p["base_h"] >= 2

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["radius"]}),
            Op("extrude", {"distance": p["base_h"]}),
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "workplane_offset",
                            "args": {
                                "offset": p["base_h"] - (p["dome_r"] - p["radius"])
                            },
                        },
                        {"name": "sphere", "args": {"radius": p["dome_r"]}},
                    ]
                },
            ),
            Op(
                "intersect",
                {
                    "ops": [
                        {
                            "name": "box",
                            "args": {
                                "length": p["radius"] * 4,
                                "width": p["radius"] * 4,
                                "height": p["base_h"] + p["dome_r"],
                                "centered": [True, True, False],
                            },
                        },
                    ]
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 6. simple_funnel (cone + cylinder)
class SimpleFunnelFamily(BaseFamily):
    name = "simple_funnel"
    standard = "N/A"
    REF = "imagined: funnel / cone with neck"

    def sample_params(self, difficulty, rng):
        return {
            "neck_r": round(float(rng.uniform(5, 12)), 1),
            "neck_h": round(float(rng.uniform(15, 30)), 1),
            "wide_r": round(float(rng.uniform(20, 35)), 1),
            "cone_h": round(float(rng.uniform(15, 30)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["wide_r"] > p["neck_r"] + 5

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["neck_r"]}),
            Op("extrude", {"distance": p["neck_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["neck_r"]}),
            Op("transformed", {"offset": [0, 0, p["cone_h"]], "rotate": [0, 0, 0]}),
            Op("circle", {"radius": p["wide_r"]}),
            Op("loft", {"combine": True}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 7. simple_handle_block (block + cylindrical handle protrusion)
class SimpleHandleBlockFamily(BaseFamily):
    name = "simple_handle_block"
    standard = "N/A"
    REF = "imagined: block with side cylindrical handle"

    def sample_params(self, difficulty, rng):
        return {
            "block_l": round(float(rng.uniform(40, 70)), 1),
            "block_w": round(float(rng.uniform(30, 50)), 1),
            "block_h": round(float(rng.uniform(20, 40)), 1),
            "handle_r": round(float(rng.uniform(5, 10)), 1),
            "handle_h": round(float(rng.uniform(15, 35)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["handle_r"] * 2 + 4 < p["block_h"]

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["block_l"],
                    "width": p["block_w"],
                    "height": p["block_h"],
                    "centered": True,
                },
            ),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["handle_r"]}),
            Op("extrude", {"distance": p["handle_h"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 8. simple_two_step_cylinder (basic stepped shaft, 2 stages)
class SimpleTwoStepCylinderFamily(BaseFamily):
    name = "simple_two_step_cylinder"
    standard = "N/A"
    REF = "imagined: simple shoulder shaft"

    def sample_params(self, difficulty, rng):
        return {
            "r1": round(float(rng.uniform(12, 25)), 1),
            "r2": round(float(rng.uniform(6, 14)), 1),
            "h1": round(float(rng.uniform(15, 30)), 1),
            "h2": round(float(rng.uniform(20, 50)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["r1"] > p["r2"] + 2 and p["h1"] >= 5 and p["h2"] >= 5

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r1"]}),
            Op("extrude", {"distance": p["h1"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["r2"]}),
            Op("extrude", {"distance": p["h2"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"stepped": True, "ref": self.REF},
        )


# 9. simple_disc_with_holes_polar (disc + polar hole array + center bore)
class SimpleDiscWithHolesPolarFamily(BaseFamily):
    name = "simple_disc_with_holes_polar"
    standard = "N/A"
    REF = "f360: drilled disc / coupling pattern"

    def sample_params(self, difficulty, rng):
        rd = round(float(rng.uniform(25, 50)), 1)
        return {
            "disc_r": rd,
            "thickness": round(float(rng.uniform(4, 12)), 1),
            "n_holes": int(rng.choice([4, 6, 8])),
            "hole_d": round(float(rng.uniform(3, 6)), 1),
            "hole_pcd": round(rd * float(rng.uniform(0.5, 0.78)), 1),
            "bore_d": round(rd * float(rng.uniform(0.15, 0.3)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["hole_pcd"] + p["hole_d"] / 2 < p["disc_r"] - 2
            and p["bore_d"] < p["hole_pcd"] - p["hole_d"]
        )

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["disc_r"]}),
            Op("extrude", {"distance": p["thickness"]}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": p["hole_pcd"],
                    "startAngle": 0,
                    "angle": 360,
                    "count": p["n_holes"],
                },
            ),
            Op("hole", {"diameter": p["hole_d"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["bore_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"polar_array": p["n_holes"], "ref": self.REF},
        )


# 10. simple_block_with_studs (box top + small spheres polar)
class SimpleBlockWithStudsFamily(BaseFamily):
    name = "simple_block_with_studs"
    standard = "N/A"
    REF = "imagined: studded baseplate (Lego-like)"

    def sample_params(self, difficulty, rng):
        return {
            "block_l": round(float(rng.uniform(50, 90)), 1),
            "block_w": round(float(rng.uniform(40, 70)), 1),
            "block_h": round(float(rng.uniform(8, 15)), 1),
            "n_x": int(rng.choice([2, 3, 4])),
            "n_y": int(rng.choice([2, 3, 4])),
            "stud_r": round(float(rng.uniform(2.5, 4.5)), 1),
            "stud_h": round(float(rng.uniform(2, 5)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        sx = p["block_l"] / (p["n_x"] + 1)
        sy = p["block_w"] / (p["n_y"] + 1)
        return p["stud_r"] * 2 + 1 < min(sx, sy)

    def make_program(self, p):
        sx = p["block_l"] / (p["n_x"] + 1)
        sy = p["block_w"] / (p["n_y"] + 1)
        ops = [
            Op(
                "box",
                {
                    "length": p["block_l"],
                    "width": p["block_w"],
                    "height": p["block_h"],
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
            Op("circle", {"radius": p["stud_r"]}),
            Op("extrude", {"distance": p["stud_h"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rarray": (p["n_x"], p["n_y"]), "ref": self.REF},
        )


# 11. simple_lid_flange (disc + ring rim + center boss + bore)
class SimpleLidFlangeFamily(BaseFamily):
    name = "simple_lid_flange"
    standard = "N/A"
    REF = "imagined: bolted lid with rim flange"

    def sample_params(self, difficulty, rng):
        rd = round(float(rng.uniform(30, 50)), 1)
        return {
            "rim_r": rd,
            "lid_r": round(rd * float(rng.uniform(0.7, 0.92)), 1),
            "rim_h": round(float(rng.uniform(4, 10)), 1),
            "lid_h": round(float(rng.uniform(2, 5)), 1),
            "boss_r": round(rd * float(rng.uniform(0.18, 0.32)), 1),
            "boss_h": round(float(rng.uniform(6, 14)), 1),
            "bore_d": round(rd * float(rng.uniform(0.08, 0.18)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["lid_r"] < p["rim_r"] - 2
            and p["boss_r"] < p["lid_r"] - 2
            and p["bore_d"] < p["boss_r"]
        )

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["rim_r"]}),
            Op("extrude", {"distance": p["rim_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["lid_r"]}),
            Op("extrude", {"distance": p["lid_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["boss_r"]}),
            Op("extrude", {"distance": p["boss_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["bore_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 12. simple_axle_yoke (rect plate with two cylindrical bosses on side)
class SimpleAxleYokeFamily(BaseFamily):
    name = "simple_axle_yoke"
    standard = "N/A"
    REF = "imagined: axle yoke / clevis arms"

    def sample_params(self, difficulty, rng):
        return {
            "base_l": round(float(rng.uniform(40, 70)), 1),
            "base_w": round(float(rng.uniform(20, 35)), 1),
            "base_h": round(float(rng.uniform(8, 16)), 1),
            "arm_r": round(float(rng.uniform(8, 14)), 1),
            "arm_h": round(float(rng.uniform(15, 30)), 1),
            "arm_offset": round(float(rng.uniform(15, 25)), 1),
            "bore_d": round(float(rng.uniform(4, 8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["arm_offset"] + p["arm_r"] < p["base_l"] / 2 + p["arm_r"]
            and p["bore_d"] < p["arm_r"] * 1.5
        )

    def make_program(self, p):
        ops = [
            Op(
                "box",
                {
                    "length": p["base_l"],
                    "width": p["base_w"],
                    "height": p["base_h"],
                    "centered": True,
                },
            ),
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": -p["arm_offset"], "y": 0}),
            Op("circle", {"radius": p["arm_r"]}),
            Op("extrude", {"distance": p["arm_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["bore_d"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": p["arm_offset"] * 2, "y": 0}),
            Op("circle", {"radius": p["arm_r"]}),
            Op("extrude", {"distance": p["arm_h"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["bore_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


ALL_FAMILIES = [
    SimpleDiscWithBossFamily,
    SimpleDiscWithPegsFamily,
    SimplePlateWithPegsFamily,
    SimpleDiscWithSkirtFamily,
    SimpleButtonFamily,
    SimpleFunnelFamily,
    SimpleHandleBlockFamily,
    SimpleTwoStepCylinderFamily,
    SimpleDiscWithHolesPolarFamily,
    SimpleBlockWithStudsFamily,
    SimpleLidFlangeFamily,
    SimpleAxleYokeFamily,
]
