"""simple_l_solid — L-cross-section solid via polyline sketch + extrude.

Different from existing l_bracket (which uses 3D box+cut). Here the L is
constructed as a single polyline outline (薄板 sketch-first style).

Variants:
  bare_l:        L outline + extrude (no features)                          (easy)
  l_with_holes:  L outline + extrude + 2 mounting holes                     (med)
  l_filleted:    L outline + extrude + outer corner fillet                  (hard)
  thick_l_cbore: L outline thick + extrude + cbore holes                    (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_l", "l_with_holes", "l_filleted", "thick_l_cbore")


def _l_outline(arm_x, arm_y, t):
    return [
        (0, 0),
        (arm_x, 0),
        (arm_x, t),
        (t, t),
        (t, arm_y),
        (0, arm_y),
    ]


class SimpleLSolidFamily(BaseFamily):
    name = "simple_l_solid"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_l"
        elif difficulty == "medium":
            v = "l_with_holes"
        else:
            v = str(rng.choice(["l_filleted", "thick_l_cbore", "l_with_holes"]))

        ax = round(float(rng.uniform(30, 70)), 1)
        ay = round(float(rng.uniform(30, 70)), 1)
        t = round(float(rng.uniform(4, 12)), 1)
        ext = round(float(rng.uniform(8, 25)), 1)
        hd = round(float(rng.uniform(3, 6)), 1)
        return {
            "variant": v,
            "arm_x": ax,
            "arm_y": ay,
            "wall_t": t,
            "extrude_depth": ext,
            "hole_d": hd,
            "fillet_r": round(min(t * 0.3, 1.5), 2),
            "cbore_d": round(hd * 1.8, 1),
            "cbore_depth": round(ext * 0.3, 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["arm_x"] > p["wall_t"] + 5
            and p["arm_y"] > p["wall_t"] + 5
            and p["wall_t"] >= 3
            and p["extrude_depth"] >= 4
        )

    def make_program(self, p):
        v = p["variant"]
        ax, ay, t, ext = p["arm_x"], p["arm_y"], p["wall_t"], p["extrude_depth"]
        pts = _l_outline(ax, ay, t)
        ops: list = []
        tags = {"variant": v, "thin_plate": True}

        ops += [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops += [Op("close", {}), Op("extrude", {"distance": ext})]

        if v == "l_with_holes":
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "pushPoints",
                    {
                        "points": [
                            (round(ax / 2, 2), round(t / 2, 2)),
                            (round(t / 2, 2), round(ay / 2, 2)),
                        ]
                    },
                ),
                Op("hole", {"diameter": p["hole_d"]}),
            ]
        elif v == "l_filleted":
            ops += [
                Op("edges", {"selector": "|Z"}),
                Op("fillet", {"radius": p["fillet_r"]}),
            ]
            tags["has_fillet"] = True
        elif v == "thick_l_cbore":
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "pushPoints",
                    {
                        "points": [
                            (round(ax * 0.7, 2), round(t / 2, 2)),
                            (round(t / 2, 2), round(ay * 0.7, 2)),
                        ]
                    },
                ),
                Op(
                    "cboreHole",
                    {
                        "diameter": p["hole_d"],
                        "cboreDiameter": p["cbore_d"],
                        "cboreDepth": p["cbore_depth"],
                    },
                ),
            ]
            tags["has_cbore"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
