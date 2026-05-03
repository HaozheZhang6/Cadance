"""simple_double_sprocket — two stacked simple_sprocket discs sharing a bore.

Variants:
  same_z:        two identical notched discs separated by a thin web   (easy/med)
  diff_z:        two discs with different tooth counts                 (med/hard)
  thin_plate_combo: one thin-plate disc + one cut-disc                 (hard, mixed style)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("same_z", "diff_z", "thin_plate_combo")


class SimpleDoubleSprocketFamily(BaseFamily):
    name = "simple_double_sprocket"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "same_z"
        elif difficulty == "medium":
            v = str(rng.choice(["same_z", "diff_z"]))
        else:
            v = str(rng.choice(VARIANTS))

        r1 = round(float(rng.uniform(15, 32)), 1)
        r2 = r1 if v == "same_z" else round(r1 * float(rng.uniform(0.55, 0.95)), 1)
        z1 = int(rng.choice([10, 12, 14, 16]))
        z2 = z1 if v == "same_z" else int(rng.choice([8, 10, 12, 14]))
        th1 = round(float(rng.uniform(3, 7)), 1)
        th2 = round(float(rng.uniform(3, 7)), 1)
        web_th = round(float(rng.uniform(2, 5)), 1)
        web_r = round(min(r1, r2) * 0.7, 1)
        bore = round(float(rng.uniform(4, max(5, min(r1, r2) * 0.4))), 1)
        return {
            "variant": v,
            "r1": r1,
            "r2": r2,
            "z1": z1,
            "z2": z2,
            "th1": th1,
            "th2": th2,
            "web_thickness": web_th,
            "web_radius": web_r,
            "tooth_h": round(min(r1, r2) * 0.13, 2),
            "bore_d": bore,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            min(p["r1"], p["r2"]) > 8
            and p["bore_d"] < p["web_radius"]
            and p["web_thickness"] >= 1.5
        )

    def make_program(self, p):
        v = p["variant"]
        r1, r2 = p["r1"], p["r2"]
        z1, z2 = p["z1"], p["z2"]
        th1, th2, wth = p["th1"], p["th2"], p["web_thickness"]
        bore = p["bore_d"]
        t_h = p["tooth_h"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        # Disc 1 (bottom)
        ops += [
            Op("circle", {"radius": r1}),
            Op("extrude", {"distance": th1}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": round(r1 + 0.1, 3),
                    "startAngle": 0,
                    "angle": 360,
                    "count": z1,
                },
            ),
            Op("rect", {"length": t_h * 2.2, "width": 2 * math.pi * r1 / z1 * 0.42}),
            Op("cutThruAll", {}),
        ]

        # Web ring (separator)
        ops += [
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": p["web_radius"]}),
            Op("extrude", {"distance": wth}),
        ]

        # Disc 2 (top)
        ops += [
            Op("workplane", {"selector": ">Z"}),
            Op("circle", {"radius": r2}),
            Op("extrude", {"distance": th2}),
        ]
        if v == "thin_plate_combo":
            # Thin-plate stylistically just means we don't notch this disc.
            tags["thin_plate"] = True
        else:
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {
                        "radius": round(r2 + 0.1, 3),
                        "startAngle": 0,
                        "angle": 360,
                        "count": z2,
                    },
                ),
                Op(
                    "rect", {"length": t_h * 2.2, "width": 2 * math.pi * r2 / z2 * 0.42}
                ),
                Op("cutThruAll", {}),
            ]

        # Through bore
        ops += [Op("workplane", {"selector": ">Z"}), Op("hole", {"diameter": bore})]
        tags["polar_array"] = max(z1, z2)

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
