"""simple_bevel_gear — cone + axial-rect-cut variants.

Variants:
  bare_cone:        revolve trapezoid profile (smooth cone)               (easy)
  truncated:        loft circle → smaller circle (frustum)                (easy)
  cone_with_bore:   cone + central bore                                   (med)
  cone_face_teeth:  truncated cone + N axial rect cuts on conical face    (med/hard)
  thin_plate_cone:  polyline (cone outline) → revolve + bore + face teeth (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = (
    "bare_cone",
    "truncated",
    "cone_with_bore",
    "cone_face_teeth",
    "thin_plate_cone",
)


class SimpleBevelGearFamily(BaseFamily):
    name = "simple_bevel_gear"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = str(rng.choice(["bare_cone", "truncated"]))
        elif difficulty == "medium":
            v = str(rng.choice(["truncated", "cone_with_bore", "cone_face_teeth"]))
        else:
            v = str(rng.choice(VARIANTS))

        r_big = round(float(rng.uniform(15, 35)), 1)
        r_small = round(r_big * float(rng.uniform(0.35, 0.65)), 1)
        h = round(float(rng.uniform(8, 22)), 1)
        z = int(rng.choice([6, 8, 10, 12]))
        bore = round(min(r_small * 0.7, float(rng.uniform(4, 10))), 1)
        return {
            "variant": v,
            "r_big": r_big,
            "r_small": r_small,
            "height": h,
            "n_teeth": z,
            "bore_d": bore,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_big"] > p["r_small"] + 2
            and p["r_small"] >= 4
            and p["height"] >= 4
            and p["bore_d"] < p["r_small"] * 2
        )

    def make_program(self, p):
        v = p["variant"]
        rb = p["r_big"]
        rs = p["r_small"]
        h = p["height"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        if v == "bare_cone":
            # Trapezoid revolved about Y axis
            pts = [(0.0, 0.0), (rb, 0.0), (rs, h), (0.0, h)]
            ops += [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
            for x, y in pts[1:]:
                ops.append(Op("lineTo", {"x": x, "y": y}))
            ops += [
                Op("close", {}),
                Op(
                    "revolve",
                    {"angleDeg": 360, "axisStart": (0, 0, 0), "axisEnd": (0, 1, 0)},
                ),
            ]
        elif v == "truncated":
            # Loft from r_big circle → r_small circle at height h
            ops += [
                Op("circle", {"radius": rb}),
                Op("transformed", {"offset": [0, 0, h], "rotate": [0, 0, 0]}),
                Op("circle", {"radius": rs}),
                Op("loft", {"combine": True}),
            ]
        elif v == "cone_with_bore":
            ops += [
                Op("circle", {"radius": rb}),
                Op("transformed", {"offset": [0, 0, h], "rotate": [0, 0, 0]}),
                Op("circle", {"radius": rs}),
                Op("loft", {"combine": True}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]
        elif v == "cone_face_teeth":
            ops += [
                Op("circle", {"radius": rb}),
                Op("transformed", {"offset": [0, 0, h], "rotate": [0, 0, 0]}),
                Op("circle", {"radius": rs}),
                Op("loft", {"combine": True}),
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {
                        "radius": rs * 0.95,
                        "startAngle": 0,
                        "angle": 360,
                        "count": p["n_teeth"],
                    },
                ),
                Op("rect", {"length": rs * 0.3, "width": rs * 0.15}),
                Op("cutBlind", {"depth": h * 0.4}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]
            tags["polar_array"] = p["n_teeth"]
        else:  # thin_plate_cone
            # Revolve trapezoid (sketch-first) + bore + cut teeth in polar array
            pts = [(p["bore_d"] / 2, 0.0), (rb, 0.0), (rs, h), (p["bore_d"] / 2, h)]
            ops += [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
            for x, y in pts[1:]:
                ops.append(Op("lineTo", {"x": x, "y": y}))
            ops += [
                Op("close", {}),
                Op(
                    "revolve",
                    {"angleDeg": 360, "axisStart": (0, 0, 0), "axisEnd": (0, 1, 0)},
                ),
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {
                        "radius": rs * 0.95,
                        "startAngle": 0,
                        "angle": 360,
                        "count": p["n_teeth"],
                    },
                ),
                Op("rect", {"length": rs * 0.25, "width": rs * 0.13}),
                Op("cutBlind", {"depth": h * 0.3}),
            ]
            tags["thin_plate"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
