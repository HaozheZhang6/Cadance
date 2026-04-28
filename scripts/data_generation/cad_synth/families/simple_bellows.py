"""simple_bellows — alternating-radius cylinder stack, mimics corrugated tube.

Variants:
  bare_tube:       single hollow cylinder (cylinder cut by smaller cylinder)   (easy)
  square_corr:     N alternating large/small radius cylinders unioned          (med, classic)
  thin_plate_corr: stepped sketch-first profile revolved (axisymmetric)        (med/hard)
  conical_corr:    corrugations with linearly tapering radii                   (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_tube", "square_corr", "thin_plate_corr", "conical_corr")


class SimpleBellowsFamily(BaseFamily):
    name = "simple_bellows"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_tube"
        elif difficulty == "medium":
            v = str(rng.choice(["square_corr", "thin_plate_corr"]))
        else:
            v = str(rng.choice(["square_corr", "thin_plate_corr", "conical_corr"]))

        r_min = round(float(rng.uniform(8, 18)), 1)
        r_max = round(r_min + float(rng.uniform(3, 8)), 1)
        seg_h = round(float(rng.uniform(2, 5)), 1)
        n_seg = int(rng.choice([4, 6, 8, 10]))
        wall = round(float(rng.uniform(1.5, 3.5)), 1)
        return {
            "variant": v,
            "r_min": r_min,
            "r_max": r_max,
            "seg_h": seg_h,
            "n_seg": n_seg,
            "wall_thickness": wall,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_min"] >= 5
            and p["r_max"] > p["r_min"]
            and p["wall_thickness"] < p["r_min"] - 1
            and p["seg_h"] >= 1.5
        )

    def make_program(self, p):
        v = p["variant"]
        r_min, r_max, sh, n, w = (
            p["r_min"],
            p["r_max"],
            p["seg_h"],
            p["n_seg"],
            p["wall_thickness"],
        )
        ops: list = []
        tags = {"variant": v, "rotational": True, "hollow": True}

        if v == "bare_tube":
            total_h = round(sh * n, 2)
            ops += [
                Op("circle", {"radius": r_max}),
                Op("extrude", {"distance": total_h}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": round((r_max - w) * 2, 3)}),
            ]
        elif v == "square_corr":
            # Stack alternating-radius cylinders; outer body first, then inner bore.
            for i in range(n):
                r_i = r_max if i % 2 == 0 else r_min
                if i == 0:
                    ops += [
                        Op("circle", {"radius": r_i}),
                        Op("extrude", {"distance": sh}),
                    ]
                else:
                    ops += [
                        Op("workplane", {"selector": ">Z"}),
                        Op("circle", {"radius": r_i}),
                        Op("extrude", {"distance": sh}),
                    ]
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": round((r_min - w) * 2, 3)}),
            ]
        elif v == "thin_plate_corr":
            # Outline polyline (square-wave radial profile) revolved.
            pts = [(r_min - w, 0.0), (r_max, 0.0)]
            y = 0.0
            for i in range(n):
                y += sh
                r_now = r_max if i % 2 == 0 else r_min
                r_next = r_min if i % 2 == 0 else r_max
                pts.append((r_now, y))
                pts.append((r_next, y))
            pts.append((r_min - w, y))
            ops += [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
            for x, yy in pts[1:]:
                ops.append(Op("lineTo", {"x": x, "y": yy}))
            ops += [
                Op("close", {}),
                Op(
                    "revolve",
                    {"angleDeg": 360, "axisStart": (0, 0, 0), "axisEnd": (0, 1, 0)},
                ),
            ]
            tags["thin_plate"] = True
        else:  # conical_corr
            # Like square_corr but each segment radius linearly tapers.
            taper = float((r_max - r_min) / max(1, n))
            for i in range(n):
                r_big = r_max - i * taper * 0.3
                r_small = r_min + i * taper * 0.1
                r_i = r_big if i % 2 == 0 else r_small
                r_i = max(r_i, p["wall_thickness"] + 1.0)
                if i == 0:
                    ops += [
                        Op("circle", {"radius": round(r_i, 3)}),
                        Op("extrude", {"distance": sh}),
                    ]
                else:
                    ops += [
                        Op("workplane", {"selector": ">Z"}),
                        Op("circle", {"radius": round(r_i, 3)}),
                        Op("extrude", {"distance": sh}),
                    ]
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": round((r_min - w) * 2, 3)}),
            ]

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
