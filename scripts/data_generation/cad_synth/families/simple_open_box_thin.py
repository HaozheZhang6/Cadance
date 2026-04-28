"""simple_open_box_thin — thin-walled open-top box (extrude rectangular ring).

薄板 box-like enclosure. Simpler than full enclosure.py; no lid, fewer features.

Variants:
  rect_ring:      single extrude of rect ring (outer rect − inner rect)    (easy)
  with_floor:     box with bottom floor (cut top instead of bottom)        (med)
  with_holes:     rect_ring + N side holes through walls                   (hard)
  rounded:        rounded rectangular ring (fillet outer corners)          (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("rect_ring", "with_floor", "with_holes", "rounded")


class SimpleOpenBoxThinFamily(BaseFamily):
    name = "simple_open_box_thin"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "rect_ring"
        elif difficulty == "medium":
            v = str(rng.choice(["with_floor", "rect_ring"]))
        else:
            v = str(rng.choice(["with_holes", "rounded", "with_floor"]))

        L = round(float(rng.uniform(40, 100)), 1)
        W = round(float(rng.uniform(30, 80)), 1)
        H = round(float(rng.uniform(15, 40)), 1)
        wall = round(float(rng.uniform(2, 5)), 1)
        floor = round(float(rng.uniform(2, 5)), 1)
        hole_d = round(float(rng.uniform(4, 10)), 1)
        n_h = int(rng.choice([2, 3, 4]))
        return {
            "variant": v,
            "length": L,
            "width": W,
            "height": H,
            "wall_thickness": wall,
            "floor_thickness": floor,
            "hole_d": hole_d,
            "n_holes": n_h,
            "fillet_r": round(float(rng.uniform(2, 6)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] > p["wall_thickness"] * 4
            and p["width"] > p["wall_thickness"] * 4
            and p["height"] >= 5
            and p["wall_thickness"] >= 1.5
        )

    def make_program(self, p):
        v = p["variant"]
        L, W, H = p["length"], p["width"], p["height"]
        w = p["wall_thickness"]
        ops: list = []
        tags = {"variant": v, "thin_plate": True, "hollow": True}

        if v == "with_floor":
            # Solid box, then shell from top
            ops += [
                Op("box", {"length": L, "width": W, "height": H, "centered": True}),
                Op("faces", {"selector": ">Z"}),
                Op("shell", {"thickness": -w}),
            ]
        elif v == "rounded":
            # Outer rounded rect − inner rounded rect (single extrude of ring)
            ops += [
                Op("rect", {"length": L, "width": W}),
                Op("rect", {"length": L - 2 * w, "width": W - 2 * w}),
                Op("extrude", {"distance": H}),
                Op("edges", {"selector": "|Z"}),
                Op("fillet", {"radius": p["fillet_r"]}),
            ]
            tags["has_fillet"] = True
        else:
            # rect_ring or with_holes — simple ring extrude
            ops += [
                Op("rect", {"length": L, "width": W}),
                Op("rect", {"length": L - 2 * w, "width": W - 2 * w}),
                Op("extrude", {"distance": H}),
            ]
            if v == "with_holes":
                # N holes on a long side wall
                n = p["n_holes"]
                # cut from face >Y (long wall facing +Y)
                spacing = L / (n + 1)
                offsets = [round((i + 1) * spacing - L / 2, 2) for i in range(n)]
                ops += [
                    Op("faces", {"selector": ">Y"}),
                    Op("workplane", {"selector": ">Y"}),
                    Op("pushPoints", {"points": [(o, H / 2) for o in offsets]}),
                    Op("hole", {"diameter": p["hole_d"]}),
                ]
                tags["has_side_holes"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
