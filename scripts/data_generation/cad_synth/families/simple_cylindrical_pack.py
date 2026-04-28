"""simple_cylindrical_pack — 15 cylindrical primitive families.

Reference: derived from F360 sample inspection. Each family is a cylinder-based
shape that recurs in mechanical parts but isn't covered by our existing
simple_<part> families.

Op pattern emphasis:
- circle/extrude (basic)
- workplane + circle/rect/extrude (multi-stage)
- chamfer / fillet on edges
- revolve (axisymmetric)
- intersect / cut for flats and grooves
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


# 1. simple_frustum_cone — pure cone frustum, no teeth (parent of simple_bevel_gear bare_cone)
class SimpleFrustumConeFamily(BaseFamily):
    name = "simple_frustum_cone"
    standard = "N/A"
    REF = "f360:138234_f169cd9e tapered cyl"

    def sample_params(self, difficulty, rng):
        rb = round(float(rng.uniform(15, 35)), 1)
        return {
            "r_big": rb,
            "r_small": round(rb * float(rng.uniform(0.3, 0.7)), 1),
            "height": round(float(rng.uniform(20, 60)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["r_big"] > p["r_small"] + 1 and p["r_small"] >= 3 and p["height"] >= 5

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_big"]}),
            Op("transformed", {"offset": [0, 0, p["height"]], "rotate": [0, 0, 0]}),
            Op("circle", {"radius": p["r_small"]}),
            Op("loft", {"combine": True}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rotational": True, "ref": self.REF},
        )


# 2. simple_d_shaft — cylinder with one chord cut (D shape extruded)
class SimpleDShaftFamily(BaseFamily):
    name = "simple_d_shaft"
    standard = "N/A"
    REF = "imagined: D-shaft for keyed coupling"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(8, 22)), 1)
        return {
            "radius": r,
            "flat_offset": round(r * float(rng.uniform(0.2, 0.5)), 1),
            "length": round(float(rng.uniform(20, 60)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] > p["flat_offset"] + 1 and p["length"] >= 10

    def make_program(self, p):
        r = p["radius"]
        # Use intersect to take the cylinder ∩ half-space (rect bigger than cyl, offset)
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": p["length"]}),
            Op(
                "intersect",
                {
                    "ops": [
                        {"name": "center", "args": {"x": 0.0, "y": p["flat_offset"]}},
                        {"name": "rect", "args": {"length": r * 3, "width": r * 2.5}},
                        {"name": "extrude", "args": {"distance": p["length"]}},
                    ]
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rotational": False, "has_flat": True, "ref": self.REF},
        )


# 3. simple_double_d_shaft — cylinder with two parallel flats (rect-cross shaft)
class SimpleDoubleDShaftFamily(BaseFamily):
    name = "simple_double_d_shaft"
    standard = "N/A"
    REF = "imagined: stepper-motor D-D shaft"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(10, 22)), 1)
        return {
            "radius": r,
            "flat_y": round(r * float(rng.uniform(0.55, 0.85)), 1),
            "length": round(float(rng.uniform(25, 60)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["flat_y"] < p["radius"] - 0.5 and p["length"] >= 10

    def make_program(self, p):
        r = p["radius"]
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": p["length"]}),
            Op(
                "intersect",
                {
                    "ops": [
                        {
                            "name": "rect",
                            "args": {"length": r * 3, "width": p["flat_y"] * 2},
                        },
                        {"name": "extrude", "args": {"distance": p["length"]}},
                    ]
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_flats": True, "ref": self.REF},
        )


# 4. simple_grooved_shaft — cylinder with annular groove cut (necked)
class SimpleGroovedShaftFamily(BaseFamily):
    name = "simple_grooved_shaft"
    standard = "N/A"
    REF = "imagined: shaft with retaining-ring groove"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(8, 20)), 1)
        L = round(float(rng.uniform(40, 80)), 1)
        return {
            "radius": r,
            "length": L,
            "groove_pos": round(L * 0.5, 1),
            "groove_w": round(float(rng.uniform(2, 5)), 1),
            "groove_depth": round(r * float(rng.uniform(0.15, 0.35)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["radius"] > p["groove_depth"] + 1
            and p["length"] >= 20
            and p["groove_w"] >= 1
        )

    def make_program(self, p):
        r = p["radius"]
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": p["length"]}),
            # Cut: use cut sub-program with cylinder ring at groove position
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "workplane_offset",
                            "args": {"offset": p["groove_pos"]},
                        },
                        {"name": "circle", "args": {"radius": r + 1}},
                        {"name": "circle", "args": {"radius": r - p["groove_depth"]}},
                        {"name": "extrude", "args": {"distance": p["groove_w"]}},
                    ]
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


# 5. simple_radial_holes_tube — cylinder with row of N transverse through holes
class SimpleRadialHolesTubeFamily(BaseFamily):
    name = "simple_radial_holes_tube"
    standard = "N/A"
    REF = "imagined: perforated tube / piston pin"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(10, 25)), 1)
        L = round(float(rng.uniform(40, 100)), 1)
        return {
            "radius": r,
            "length": L,
            "n_holes": int(rng.choice([2, 3, 4, 5])),
            "hole_d": round(r * float(rng.uniform(0.18, 0.35)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["hole_d"] < p["radius"] and p["length"] >= 20

    def make_program(self, p):
        r = p["radius"]
        L = p["length"]
        n = p["n_holes"]
        # Build solid cylinder
        ops = [Op("circle", {"radius": r}), Op("extrude", {"distance": L})]
        # Holes from front face (>Y) — switch workplane to YZ-style face on cylinder
        # Use cut sub-programs
        spacing = L / (n + 1)
        for i in range(n):
            zpos = round((i + 1) * spacing, 2)
            ops += [
                Op(
                    "cut",
                    {
                        "ops": [
                            {"name": "workplane_offset", "args": {"offset": zpos}},
                            {
                                "name": "rect",
                                "args": {"length": r * 2.5, "width": p["hole_d"]},
                            },
                            {
                                "name": "extrude",
                                "args": {"distance": -1},
                            },  # placeholder
                        ]
                    },
                ),
            ]
        # Easier: just use rarray + axial cylinders
        # Replace ops above with simpler hole approach:
        ops = [Op("circle", {"radius": r}), Op("extrude", {"distance": L})]
        # Use polarArray on a face — not available. Use rarray on top.
        ops += [
            Op("workplane", {"selector": ">Z"}),
            Op(
                "rarray", {"xSpacing": 1, "ySpacing": spacing, "xCount": 1, "yCount": n}
            ),
            # Re-position via center is awkward; use pushPoints instead
        ]
        # Cleaner: pushPoints + hole on top face (cuts through whole cylinder)
        offsets = [round((i + 1) * spacing - L / 2, 2) for i in range(n)]
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": L}),
        ]
        # Through-holes are transverse — i.e., perpendicular to cylinder axis. Need
        # workplane on the side face. Use a side cut via cut sub-program (rect in XZ).
        for off in offsets:
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XZ",
                        "ops": [
                            {"name": "moveTo", "args": {"x": 0.0, "y": off + L / 2}},
                            {"name": "circle", "args": {"radius": p["hole_d"] / 2}},
                            {
                                "name": "extrude",
                                "args": {"distance": r * 2.5, "both": True},
                            },
                        ],
                    },
                )
            )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"n_holes": n, "ref": self.REF},
        )


# 6. simple_axial_slot_cylinder — cylinder + 1 axial slot cut
class SimpleAxialSlotCylinderFamily(BaseFamily):
    name = "simple_axial_slot_cylinder"
    standard = "N/A"
    REF = "imagined: slotted shaft / yoke"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(10, 25)), 1)
        L = round(float(rng.uniform(30, 70)), 1)
        return {
            "radius": r,
            "length": L,
            "slot_w": round(r * float(rng.uniform(0.25, 0.45)), 1),
            "slot_depth": round(r * float(rng.uniform(0.5, 0.95)), 1),
            "slot_l": round(L * float(rng.uniform(0.4, 0.8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["slot_depth"] < p["radius"] - 1
            and p["slot_w"] < p["radius"]
            and p["slot_l"] < p["length"] - 4
        )

    def make_program(self, p):
        r = p["radius"]
        L = p["length"]
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": L}),
            Op("workplane", {"selector": ">Z"}),
            Op("rect", {"length": p["slot_w"], "width": p["slot_l"]}),
            Op("cutBlind", {"depth": p["slot_depth"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_slot": True, "ref": self.REF},
        )


# 7. simple_chamfer_shaft — cylinder + chamfer both ends
class SimpleChamferShaftFamily(BaseFamily):
    name = "simple_chamfer_shaft"
    standard = "N/A"
    REF = "imagined: machined shaft with chamfered ends"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(8, 25)), 1)
        return {
            "radius": r,
            "length": round(float(rng.uniform(30, 100)), 1),
            "chamfer": round(r * float(rng.uniform(0.1, 0.3)), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["chamfer"] > 0.2 and p["length"] >= 10

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["radius"]}),
            Op("extrude", {"distance": p["length"]}),
            Op("edges", {"selector": ">Z"}),
            Op("chamfer", {"length": p["chamfer"]}),
            Op("edges", {"selector": "<Z"}),
            Op("chamfer", {"length": p["chamfer"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_chamfer": True, "ref": self.REF},
        )


# 8. simple_stepped_shaft_basic — long-axis varying radius cylinder (3-step)
class SimpleSteppedShaftBasicFamily(BaseFamily):
    name = "simple_stepped_shaft_basic"
    standard = "N/A"
    REF = "imagined: machined stepped shaft"

    def sample_params(self, difficulty, rng):
        r1 = round(float(rng.uniform(8, 18)), 1)
        return {
            "r1": r1,
            "r2": round(r1 * float(rng.uniform(1.2, 1.6)), 1),
            "r3": round(r1 * float(rng.uniform(0.7, 0.95)), 1),
            "h1": round(float(rng.uniform(15, 35)), 1),
            "h2": round(float(rng.uniform(10, 25)), 1),
            "h3": round(float(rng.uniform(15, 35)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return all(p[k] >= 4 for k in ("r1", "r2", "r3", "h1", "h2", "h3"))

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r1"]}),
            Op("extrude", {"distance": p["h1"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["r2"]}),
            Op("extrude", {"distance": p["h2"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["r3"]}),
            Op("extrude", {"distance": p["h3"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"multi_stage": True, "ref": self.REF},
        )


# 9. simple_hollow_pipe — concentric cylinders single-extrude (annular ring extrude)
class SimpleHollowPipeFamily(BaseFamily):
    name = "simple_hollow_pipe"
    standard = "N/A"
    REF = "imagined: pipe / sleeve / bushing"

    def sample_params(self, difficulty, rng):
        ro = round(float(rng.uniform(15, 35)), 1)
        return {
            "r_outer": ro,
            "r_inner": round(ro * float(rng.uniform(0.55, 0.85)), 1),
            "length": round(float(rng.uniform(25, 80)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["r_outer"] > p["r_inner"] + 1 and p["length"] >= 10

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_outer"]}),
            Op("circle", {"radius": p["r_inner"]}),
            Op("extrude", {"distance": p["length"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"hollow": True, "ref": self.REF},
        )


# 10. simple_thin_disc — short cylinder
class SimpleThinDiscFamily(BaseFamily):
    name = "simple_thin_disc"
    standard = "N/A"
    REF = "f360:24086_a8e5514c thin disc"

    def sample_params(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(20, 50)), 1),
            "thickness": round(float(rng.uniform(2, 8)), 1),
            "with_chamfer": (difficulty == "hard" and rng.uniform(0, 1) < 0.5),
            "chamfer": round(float(rng.uniform(0.4, 1.0)), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] >= 8 and p["thickness"] >= 1.0

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["radius"]}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        if p.get("with_chamfer"):
            ops += [
                Op("edges", {"selector": ">Z"}),
                Op("chamfer", {"length": p["chamfer"]}),
            ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "ref": self.REF},
        )


# 11. simple_thick_ring — chunky annular ring
class SimpleThickRingFamily(BaseFamily):
    name = "simple_thick_ring"
    standard = "N/A"
    REF = "f360:41780_da6cd1db ring"

    def sample_params(self, difficulty, rng):
        ro = round(float(rng.uniform(20, 40)), 1)
        return {
            "r_outer": ro,
            "r_inner": round(ro * float(rng.uniform(0.4, 0.7)), 1),
            "thickness": round(float(rng.uniform(8, 25)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["r_outer"] > p["r_inner"] + 2 and p["thickness"] >= 4

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_outer"]}),
            Op("circle", {"radius": p["r_inner"]}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"hollow": True, "ref": self.REF},
        )


# 12. simple_hemisphere — sphere intersected with half-space (cut via box)
class SimpleHemisphereFamily(BaseFamily):
    name = "simple_hemisphere"
    standard = "N/A"
    REF = "imagined: hemisphere shell / dome"

    def sample_params(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 40)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] >= 5

    def make_program(self, p):
        r = p["radius"]
        ops = [
            Op("sphere", {"radius": r}),
            Op(
                "intersect",
                {
                    "ops": [
                        {
                            "name": "box",
                            "args": {
                                "length": r * 3,
                                "width": r * 3,
                                "height": r * 2,
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
            feature_tags={"rotational": True, "ref": self.REF},
        )


# 13. simple_tapered_pin — sharp pointed cone (e.g. drill point)
class SimpleTaperedPinFamily(BaseFamily):
    name = "simple_tapered_pin"
    standard = "N/A"
    REF = "imagined: alignment pin / drill tip"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(4, 12)), 1)
        return {
            "radius": r,
            "height": round(float(rng.uniform(20, 60)), 1),
            "tip_r": round(r * float(rng.uniform(0.05, 0.3)), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] > p["tip_r"] and p["height"] >= 8

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["radius"]}),
            Op("transformed", {"offset": [0, 0, p["height"]], "rotate": [0, 0, 0]}),
            Op("circle", {"radius": p["tip_r"]}),
            Op("loft", {"combine": True}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rotational": True, "ref": self.REF},
        )


# 14. simple_capsule_3d — cylinder + hemisphere on each end
class SimpleCapsule3dFamily(BaseFamily):
    name = "simple_capsule_3d"
    standard = "N/A"
    REF = "imagined: 3D pill / capsule / round-end shaft"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(8, 20)), 1)
        return {
            "radius": r,
            "length": round(float(rng.uniform(30, 70)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] >= 4 and p["length"] >= p["radius"] * 1.5

    def make_program(self, p):
        r = p["radius"]
        L = p["length"]
        # Build cylinder (height = L - 2r) + 2 spheres at ends
        cyl_h = L - 2 * r
        ops = [
            Op("circle", {"radius": r}),
            Op("extrude", {"distance": cyl_h}),
            Op(
                "union",
                {
                    "ops": [
                        {"name": "sphere", "args": {"radius": r}},
                    ]
                },
            ),
            Op(
                "union",
                {
                    "ops": [
                        {"name": "workplane_offset", "args": {"offset": cyl_h}},
                        {"name": "sphere", "args": {"radius": r}},
                    ]
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"rotational": True, "ref": self.REF},
        )


# 15. simple_grooved_disc — disc with annular V-groove cut on one face
class SimpleGroovedDiscFamily(BaseFamily):
    name = "simple_grooved_disc"
    standard = "N/A"
    REF = "imagined: pulley face / brake disc"

    def sample_params(self, difficulty, rng):
        ro = round(float(rng.uniform(20, 40)), 1)
        return {
            "r_outer": ro,
            "groove_r": round(ro * float(rng.uniform(0.4, 0.75)), 1),
            "groove_w": round(float(rng.uniform(2, 6)), 1),
            "groove_depth": round(float(rng.uniform(2, 5)), 1),
            "thickness": round(float(rng.uniform(8, 18)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["groove_r"] < p["r_outer"] - 2 and p["groove_depth"] < p["thickness"] - 2
        )

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_outer"]}),
            Op("extrude", {"distance": p["thickness"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["groove_r"] + p["groove_w"] / 2}),
            Op("circle", {"radius": p["groove_r"] - p["groove_w"] / 2}),
            Op("cutBlind", {"depth": p["groove_depth"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"has_groove": True, "ref": self.REF},
        )


ALL_FAMILIES = [
    SimpleFrustumConeFamily,
    SimpleDShaftFamily,
    SimpleDoubleDShaftFamily,
    SimpleGroovedShaftFamily,
    SimpleRadialHolesTubeFamily,
    SimpleAxialSlotCylinderFamily,
    SimpleChamferShaftFamily,
    SimpleSteppedShaftBasicFamily,
    SimpleHollowPipeFamily,
    SimpleThinDiscFamily,
    SimpleThickRingFamily,
    SimpleHemisphereFamily,
    SimpleTaperedPinFamily,
    SimpleCapsule3dFamily,
    SimpleGroovedDiscFamily,
]
