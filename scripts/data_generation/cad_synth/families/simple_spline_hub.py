"""simple_spline_hub — cylinder with N axial rectangular slots.

Variants:
  bare_cyl:       hollow cylinder + bore                                  (easy)
  axial_slots:    cylinder + N rectangular slots cut along axis           (med)
  thin_plate_hub: gear-like polyline (square teeth on inner bore) extrude (hard, internal teeth)
  external_keys:  cylinder + N polar-array keyway-like external bumps    (hard)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_cyl", "axial_slots", "thin_plate_hub", "external_keys")


def _internal_spline_outline(r_out, r_root, n, tooth_frac=0.5):
    """Outer circle outline OR inner-spline profile pts."""
    pts = []
    pitch = 2 * math.pi / n
    half_t = pitch * tooth_frac / 2
    # Internal teeth: outer is r_out (smooth ring), inner has crenellations.
    # Just return the inner crenellated profile here (caller composes).
    for i in range(n):
        c = i * pitch
        a0 = c - pitch / 2
        a1 = c - half_t
        a2 = c + half_t
        for ang, r in [
            (a0, r_out),
            (a1, r_out),
            (a1, r_root),
            (a2, r_root),
            (a2, r_out),
        ]:
            pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    return pts


class SimpleSplineHubFamily(BaseFamily):
    name = "simple_spline_hub"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_cyl"
        elif difficulty == "medium":
            v = "axial_slots"
        else:
            v = str(rng.choice(["axial_slots", "thin_plate_hub", "external_keys"]))

        r = round(float(rng.uniform(8, 22)), 1)
        h = round(float(rng.uniform(10, 30)), 1)
        n = int(rng.choice([4, 6, 8, 10, 12]))
        bore = round(float(rng.uniform(3, max(4, r * 0.5))), 1)
        slot_w = round(float(rng.uniform(1.5, 3.0)), 2)
        slot_d = round(float(rng.uniform(1.5, 4.0)), 2)
        return {
            "variant": v,
            "radius": r,
            "height": h,
            "n_features": n,
            "bore_d": bore,
            "slot_w": slot_w,
            "slot_d": slot_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["radius"] >= 5
            and p["height"] >= 4
            and p["bore_d"] < p["radius"] * 1.6
            and p["bore_d"] >= 2
        )

    def make_program(self, p):
        v = p["variant"]
        r, h, n = p["radius"], p["height"], p["n_features"]
        bore = p["bore_d"]
        sw = p["slot_w"]
        sd = p["slot_d"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        if v == "bare_cyl":
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
        elif v == "axial_slots":
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {"radius": r - sd / 2, "startAngle": 0, "angle": 360, "count": n},
                ),
                Op("rect", {"length": sw, "width": sd}),
                Op("cutThruAll", {}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = n
        elif v == "thin_plate_hub":
            # Outer smooth circle + inner crenellated outline via sketch_subtract.
            r_inner = round(bore / 2 + sd, 3)
            inner_pts = _internal_spline_outline(r_inner, bore / 2, n)
            ops += [
                Op(
                    "sketch_subtract",
                    {
                        "outer_radius": r,
                        "profiles": [
                            {
                                "wire_ops": [
                                    {"name": "polyline", "args": {"points": inner_pts}},
                                    {"name": "close", "args": {}},
                                ]
                            }
                        ],
                    },
                ),
                Op("placeSketch", {}),
                Op("extrude", {"distance": h}),
            ]
            tags["thin_plate"] = True
            tags["sketch_subtract"] = True
        else:  # external_keys
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": "<Z"}),
                Op(
                    "polarArray",
                    {"radius": r + sd / 2, "startAngle": 0, "angle": 360, "count": n},
                ),
                Op("rect", {"length": sd * 2, "width": sw}),
                Op("extrude", {"distance": h}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = n
            tags["external"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
