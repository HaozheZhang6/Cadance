"""simple_helical_gear — twistExtrude variants of simple_spur_gear.

Variants:
  bare_twist:    circle → twistExtrude (no teeth, just a twisted disc)         (easy)
  twist_polygon: regular polygon → twistExtrude (acts as N rectangular teeth)  (med/hard)
  thin_plate_twist: square-toothed polyline → twistExtrude                     (hard, sketch-first)
  twist_then_bore: any twistExtrude solid + central bore                       (med/hard)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_twist", "twist_polygon", "thin_plate_twist", "twist_then_bore")


def _square_tooth_outline(r_root: float, r_tip: float, z: int, tf: float = 0.5):
    pts = []
    pitch = 2 * math.pi / z
    half_t = pitch * tf / 2
    for i in range(z):
        c = i * pitch
        a0 = c - pitch / 2
        a1 = c - half_t
        a2 = c + half_t
        for ang, r in [
            (a0, r_root),
            (a1, r_root),
            (a1, r_tip),
            (a2, r_tip),
            (a2, r_root),
        ]:
            pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    return pts


class SimpleHelicalGearFamily(BaseFamily):
    name = "simple_helical_gear"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = str(rng.choice(["bare_twist", "bare_twist", "twist_then_bore"]))
        elif difficulty == "medium":
            v = str(rng.choice(["twist_polygon", "twist_then_bore"]))
        else:
            v = str(rng.choice(VARIANTS))

        r = round(float(rng.uniform(12, 30)), 1)
        h = round(float(rng.uniform(15, 50)), 1)
        twist = float(rng.choice([15, 25, 35, 45, 60]))
        z = int(rng.choice([6, 8, 10, 12, 14, 16]))
        bore = round(float(rng.uniform(3, max(4, r * 0.45))), 1)

        p = {
            "variant": v,
            "radius": r,
            "height": h,
            "twist_deg": twist,
            "n_teeth": z,
            "tooth_h": round(r * float(rng.uniform(0.08, 0.18)), 2),
            "bore_d": bore,
            "difficulty": difficulty,
        }
        return p

    def validate_params(self, p):
        return p["radius"] >= 6 and p["height"] >= 5 and p["bore_d"] < p["radius"] * 1.3

    def make_program(self, p):
        v = p["variant"]
        r = p["radius"]
        h = p["height"]
        tw = p["twist_deg"]
        z = p["n_teeth"]
        ops: list = []
        tags = {"variant": v, "rotational": True, "twist_deg": tw}

        if v == "bare_twist":
            ops += [
                Op("circle", {"radius": r}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
            ]
            if p["bore_d"] > 0:
                ops += [
                    Op("workplane", {"selector": ">Z"}),
                    Op("hole", {"diameter": p["bore_d"]}),
                ]
        elif v == "twist_polygon":
            ops += [
                Op("polygon", {"n": z, "diameter": r * 2}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]
        elif v == "thin_plate_twist":
            r_root = round(r - p["tooth_h"] * 0.5, 3)
            r_tip = round(r + p["tooth_h"] * 0.5, 3)
            pts = _square_tooth_outline(r_root, r_tip, z)
            ops += [
                Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}),
                Op("polyline", {"points": pts[1:] + [pts[0]]}),
                Op("close", {}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]
            tags["thin_plate"] = True
        else:  # twist_then_bore — disc with twist then through bore
            ops += [
                Op("circle", {"radius": r}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": p["bore_d"]}),
            ]

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
