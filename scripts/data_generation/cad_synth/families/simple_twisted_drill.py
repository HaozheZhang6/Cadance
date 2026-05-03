"""simple_twisted_drill — twistExtrude on simple profiles.

Variants:
  square_twist:   square section twistExtrude                       (easy)
  cross_twist:    cross/plus section twistExtrude                   (med)
  star_twist:     5-point star twistExtrude                         (hard)
  shanked:        smooth cylinder shank + twisted flute below       (hard, two stage)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("square_twist", "cross_twist", "star_twist", "shanked")


def _star_pts(r_out, r_in, n=5):
    pts = []
    for i in range(2 * n):
        ang = math.pi / 2 - i * math.pi / n
        rr = r_out if i % 2 == 0 else r_in
        pts.append((round(rr * math.cos(ang), 4), round(rr * math.sin(ang), 4)))
    return pts


def _cross_pts(s, a):
    return [
        (-a / 2, -s / 2),
        (a / 2, -s / 2),
        (a / 2, -a / 2),
        (s / 2, -a / 2),
        (s / 2, a / 2),
        (a / 2, a / 2),
        (a / 2, s / 2),
        (-a / 2, s / 2),
        (-a / 2, a / 2),
        (-s / 2, a / 2),
        (-s / 2, -a / 2),
        (-a / 2, -a / 2),
    ]


class SimpleTwistedDrillFamily(BaseFamily):
    name = "simple_twisted_drill"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "square_twist"
        elif difficulty == "medium":
            v = str(rng.choice(["square_twist", "cross_twist"]))
        else:
            v = str(rng.choice(VARIANTS))

        r = round(float(rng.uniform(4, 12)), 1)
        h = round(float(rng.uniform(20, 60)), 1)
        twist = float(rng.choice([180, 270, 360, 540, 720]))
        shank_h = round(h * float(rng.uniform(0.2, 0.4)), 1)
        return {
            "variant": v,
            "radius": r,
            "height": h,
            "twist_deg": twist,
            "shank_h": shank_h,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["radius"] >= 2 and p["height"] >= 8

    def make_program(self, p):
        v = p["variant"]
        r, h, tw = p["radius"], p["height"], p["twist_deg"]
        ops: list = []
        tags = {"variant": v, "twist_deg": tw, "rotational": False}

        if v == "square_twist":
            ops += [
                Op("rect", {"length": r * 2, "width": r * 2}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
            ]
        elif v == "cross_twist":
            pts = _cross_pts(r * 2, r * 0.7)
            ops += [
                Op("polyline", {"points": pts}),
                Op("close", {}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
            ]
            tags["polyline"] = True
        elif v == "star_twist":
            pts = _star_pts(r, r * 0.5, n=5)
            ops += [
                Op("polyline", {"points": pts}),
                Op("close", {}),
                Op("twistExtrude", {"distance": h, "angle": tw}),
            ]
            tags["polyline"] = True
        else:  # shanked
            sh = p["shank_h"]
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": sh}),
                Op("workplane", {"selector": ">Z"}),
                Op("rect", {"length": r * 1.6, "width": r * 1.6}),
                Op("twistExtrude", {"distance": h - sh, "angle": tw}),
            ]
            tags["two_stage"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
