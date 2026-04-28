"""simple_multi_extrude_step — multi-stage sketch+extrude composition.

Inspired by Fusion360 designs that show a base + boss + cap pattern (3 sketches
on stacked workplanes). Each variant exercises a different boss-shape combo.

Variants:
  cyl_box_cyl:   bottom cylinder + middle box + top cylinder         (easy/med)
  box_cyl_box:   alternating box/cyl/box                              (med)
  poly_circ_rect: polygon base + circle middle + rect top             (hard, mixed)
  rect_with_chamfer_top: simple box+box with top chamfer              (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("cyl_box_cyl", "box_cyl_box", "poly_circ_rect", "rect_with_chamfer_top")


class SimpleMultiExtrudeStepFamily(BaseFamily):
    name = "simple_multi_extrude_step"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "cyl_box_cyl"
        elif difficulty == "medium":
            v = str(rng.choice(["cyl_box_cyl", "box_cyl_box"]))
        else:
            v = str(
                rng.choice(["poly_circ_rect", "rect_with_chamfer_top", "box_cyl_box"])
            )

        s = round(float(rng.uniform(15, 35)), 1)
        s2 = round(s * float(rng.uniform(0.55, 0.85)), 1)
        s3 = round(s2 * float(rng.uniform(0.55, 0.9)), 1)
        h = round(float(rng.uniform(6, 14)), 1)
        return {
            "variant": v,
            "s1": s,
            "s2": s2,
            "s3": s3,
            "h_each": h,
            "polygon_n": int(rng.choice([5, 6, 8])),
            "chamfer": round(float(rng.uniform(0.5, 2)), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["s1"] > p["s2"] > p["s3"] > 4 and p["h_each"] >= 3

    def make_program(self, p):
        v = p["variant"]
        s1, s2, s3, h = p["s1"], p["s2"], p["s3"], p["h_each"]
        ops: list = []
        tags = {"variant": v, "multi_stage": True}

        if v == "cyl_box_cyl":
            ops += [
                Op("circle", {"radius": s1}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("rect", {"length": s2 * 1.4, "width": s2}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("circle", {"radius": s3}),
                Op("extrude", {"distance": h}),
            ]
        elif v == "box_cyl_box":
            ops += [
                Op("rect", {"length": s1 * 1.4, "width": s1}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("circle", {"radius": s2}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("rect", {"length": s3 * 1.4, "width": s3}),
                Op("extrude", {"distance": h}),
            ]
        elif v == "poly_circ_rect":
            ops += [
                Op("polygon", {"n": p["polygon_n"], "diameter": s1 * 2}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("circle", {"radius": s2}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("rect", {"length": s3 * 1.4, "width": s3}),
                Op("extrude", {"distance": h}),
            ]
        else:  # rect_with_chamfer_top
            ops += [
                Op("rect", {"length": s1 * 1.4, "width": s1}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("rect", {"length": s2 * 1.4, "width": s2}),
                Op("extrude", {"distance": h}),
                Op("edges", {"selector": ">Z"}),
                Op("chamfer", {"length": p["chamfer"]}),
            ]
            tags["has_chamfer"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
