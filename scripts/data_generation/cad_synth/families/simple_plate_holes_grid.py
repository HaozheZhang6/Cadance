"""simple_plate_holes_grid — thin rectangular plate with rect-grid of circular holes.

Inspired by Fusion360/DeepCAD-style flat sheet metal parts.
薄板 + rarray + hole composition.

Variants:
  no_holes:       plate only                                  (easy)
  full_grid:      mx × my regular grid of through holes       (med)
  staggered:      mx × my grid with row-offset (brick layout) (hard)
  mixed_holes:    grid of through-holes + row of cbore holes  (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("no_holes", "full_grid", "staggered", "mixed_holes")


class SimplePlateHolesGridFamily(BaseFamily):
    name = "simple_plate_holes_grid"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "no_holes"
        elif difficulty == "medium":
            v = str(rng.choice(["full_grid", "full_grid"]))
        else:
            v = str(rng.choice(["staggered", "mixed_holes", "full_grid"]))

        L = round(float(rng.uniform(40, 100)), 1)
        W = round(float(rng.uniform(30, 80)), 1)
        T = round(float(rng.uniform(2, 6)), 1)
        mx = int(rng.choice([2, 3, 4, 5]))
        my = int(rng.choice([2, 3, 4, 5]))
        hole_d = round(float(rng.uniform(2.5, 6)), 1)
        cbore_d = round(hole_d * float(rng.uniform(1.6, 2.2)), 1)
        cbore_depth = round(T * float(rng.uniform(0.3, 0.5)), 2)
        return {
            "variant": v,
            "length": L,
            "width": W,
            "thickness": T,
            "n_x": mx,
            "n_y": my,
            "hole_d": hole_d,
            "cbore_d": cbore_d,
            "cbore_depth": cbore_depth,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] >= 20
            and p["width"] >= 20
            and p["thickness"] >= 1.5
            and p["hole_d"]
            < min(p["length"] / (p["n_x"] + 1.5), p["width"] / (p["n_y"] + 1.5))
        )

    def make_program(self, p):
        v = p["variant"]
        L, W, T = p["length"], p["width"], p["thickness"]
        mx, my = p["n_x"], p["n_y"]
        hd = p["hole_d"]
        ops: list = []
        tags = {"variant": v, "thin_plate": True}

        # Plate
        ops += [Op("rect", {"length": L, "width": W}), Op("extrude", {"distance": T})]

        if v == "no_holes":
            return Program(
                family=self.name,
                difficulty=p["difficulty"],
                params=p,
                ops=ops,
                feature_tags=tags,
            )

        sx = round(L / (mx + 1), 2)
        sy = round(W / (my + 1), 2)
        ops += [Op("workplane", {"selector": ">Z"})]

        if v == "full_grid":
            ops += [
                Op(
                    "rarray",
                    {"xSpacing": sx, "ySpacing": sy, "xCount": mx, "yCount": my},
                ),
                Op("hole", {"diameter": hd}),
            ]
            tags["rarray"] = (mx, my)
        elif v == "staggered":
            # Two row sets offset by half spacing
            ops += [
                Op(
                    "rarray",
                    {
                        "xSpacing": sx,
                        "ySpacing": sy * 2,
                        "xCount": mx,
                        "yCount": max(1, my // 2),
                    },
                ),
                Op("hole", {"diameter": hd}),
                Op("workplane", {"selector": ">Z"}),
                Op("center", {"x": sx / 2, "y": sy}),
                Op(
                    "rarray",
                    {
                        "xSpacing": sx,
                        "ySpacing": sy * 2,
                        "xCount": max(1, mx - 1),
                        "yCount": max(1, my // 2),
                    },
                ),
                Op("hole", {"diameter": hd}),
            ]
            tags["rarray"] = (mx, my)
        else:  # mixed_holes — grid + cbore row
            ops += [
                Op(
                    "rarray",
                    {"xSpacing": sx, "ySpacing": sy, "xCount": mx, "yCount": my},
                ),
                Op("hole", {"diameter": hd}),
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "rarray",
                    {
                        "xSpacing": sx,
                        "ySpacing": sy * (my + 1),
                        "xCount": mx,
                        "yCount": 1,
                    },
                ),
                Op(
                    "cboreHole",
                    {
                        "diameter": hd,
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
