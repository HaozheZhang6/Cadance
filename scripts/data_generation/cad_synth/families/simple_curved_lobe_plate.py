"""simple_curved_lobe_plate — circular plate with N semicircular lobes/scallops.

Sketch-first single-extrude. Lobes via threePointArc segments along outline.

Variants:
  scallop:        plate with N inward scallops (concave bumps)              (easy)
  lobe:           plate with N outward lobes (convex bumps)                 (med)
  lobe_with_bore: lobed plate + central bore                                (med)
  lobe_with_holes: lobed plate + bore + N small holes at lobes              (hard)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("scallop", "lobe", "lobe_with_bore", "lobe_with_holes")


class SimpleCurvedLobePlateFamily(BaseFamily):
    name = "simple_curved_lobe_plate"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = str(rng.choice(["scallop", "lobe"]))
        elif difficulty == "medium":
            v = str(rng.choice(["lobe_with_bore", "lobe"]))
        else:
            v = str(rng.choice(["lobe_with_holes", "lobe_with_bore"]))

        r_base = round(float(rng.uniform(20, 40)), 1)
        n_lobe = int(rng.choice([4, 5, 6, 8, 10]))
        lobe_amp = round(r_base * float(rng.uniform(0.06, 0.16)), 2)
        T = round(float(rng.uniform(3, 8)), 1)
        bore = round(float(rng.uniform(4, 10)), 1)
        small_d = round(float(rng.uniform(2, 4)), 1)
        return {
            "variant": v,
            "base_radius": r_base,
            "n_lobes": n_lobe,
            "lobe_amplitude": lobe_amp,
            "thickness": T,
            "bore_d": bore,
            "small_hole_d": small_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["base_radius"] >= 10
            and p["thickness"] >= 2
            and p["bore_d"] < p["base_radius"] * 1.2
        )

    def make_program(self, p):
        v = p["variant"]
        r = p["base_radius"]
        n = p["n_lobes"]
        amp = p["lobe_amplitude"]
        T = p["thickness"]
        sign = -1 if v == "scallop" else 1
        # Approximate lobed outline as polyline of 4n points (modulating radius sinusoidally)
        n_pts = max(60, n * 12)
        pts = []
        for i in range(n_pts):
            ang = 2 * math.pi * i / n_pts
            r_now = r + sign * amp * math.cos(n * ang)
            pts.append(
                (round(r_now * math.cos(ang), 4), round(r_now * math.sin(ang), 4))
            )
        ops: list = []
        tags = {"variant": v, "thin_plate": True, "n_lobes": n}

        ops += [
            Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}),
            Op("polyline", {"points": pts[1:] + [pts[0]]}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
        ]

        if v in ("lobe_with_bore", "lobe_with_holes"):
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]
        if v == "lobe_with_holes":
            pcd = round(r * 0.7, 2)
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {"radius": pcd, "startAngle": 0, "angle": 360, "count": n},
                ),
                Op("hole", {"diameter": p["small_hole_d"]}),
            ]
            tags["polar_array"] = n

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
