"""simple_t_solid — T-cross-section extruded solid.

薄板 polyline + extrude. Like an aluminum T-extrusion.

Variants:
  bare_t:       T outline + extrude                                       (easy)
  t_with_slot:  T + center slot through                                   (med)
  t_with_holes: T + N holes along stem                                    (med)
  t_with_chamfer: T + top chamfer on flange edges                         (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_t", "t_with_slot", "t_with_holes", "t_with_chamfer")


def _t_outline(flange_w, flange_t, stem_w, stem_h):
    # Origin at bottom of stem
    return [
        (-stem_w / 2, 0),
        (stem_w / 2, 0),
        (stem_w / 2, stem_h),
        (flange_w / 2, stem_h),
        (flange_w / 2, stem_h + flange_t),
        (-flange_w / 2, stem_h + flange_t),
        (-flange_w / 2, stem_h),
        (-stem_w / 2, stem_h),
    ]


class SimpleTSolidFamily(BaseFamily):
    name = "simple_t_solid"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_t"
        elif difficulty == "medium":
            v = str(rng.choice(["t_with_slot", "t_with_holes"]))
        else:
            v = str(rng.choice(["t_with_chamfer", "t_with_holes"]))

        fw = round(float(rng.uniform(40, 80)), 1)
        ft = round(float(rng.uniform(4, 10)), 1)
        sw = round(float(rng.uniform(6, 14)), 1)
        sh = round(float(rng.uniform(20, 40)), 1)
        ext = round(float(rng.uniform(15, 50)), 1)
        return {
            "variant": v,
            "flange_w": fw,
            "flange_t": ft,
            "stem_w": sw,
            "stem_h": sh,
            "extrude_depth": ext,
            "n_holes": int(rng.choice([2, 3, 4])),
            "hole_d": round(float(rng.uniform(2, 5)), 1),
            "slot_w": round(sw * 0.4, 1),
            "slot_h": round(sh * 0.5, 1),
            "chamfer": round(min(ft * 0.4, 2.0), 2),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["flange_w"] > p["stem_w"] + 4
            and p["stem_h"] >= 8
            and p["flange_t"] >= 3
            and p["extrude_depth"] >= 5
        )

    def make_program(self, p):
        v = p["variant"]
        fw, ft, sw, sh = p["flange_w"], p["flange_t"], p["stem_w"], p["stem_h"]
        ext = p["extrude_depth"]
        pts = _t_outline(fw, ft, sw, sh)
        ops: list = []
        tags = {"variant": v, "thin_plate": True}

        ops += [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops += [Op("close", {}), Op("extrude", {"distance": ext})]

        if v == "t_with_slot":
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("center", {"x": 0.0, "y": sh / 2}),
                Op("rect", {"length": p["slot_w"], "width": p["slot_h"]}),
                Op("cutThruAll", {}),
            ]
            tags["has_slot"] = True
        elif v == "t_with_holes":
            n = p["n_holes"]
            ops += [Op("workplane", {"selector": ">Z"})]
            offsets = [round((i - (n - 1) / 2) * sh / (n + 1), 2) for i in range(n)]
            ops += [
                Op("pushPoints", {"points": [(0.0, sh / 2 + o) for o in offsets]}),
                Op("hole", {"diameter": p["hole_d"]}),
            ]
        elif v == "t_with_chamfer":
            ops += [
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
