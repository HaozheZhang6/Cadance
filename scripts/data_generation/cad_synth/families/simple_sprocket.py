"""simple_sprocket — square-tooth disc with bore + optional hub.

Same shape family as simple_spur_gear but emphasis on:
  - thicker disc + hub stub (sprocket-style)
  - chamfered tip edges
  - smaller tooth_frac → looks like ratchet/sprocket teeth

Variants:
  notched_disc:    disc + polarArray rect cut (root notches between teeth)  (easy)
  thin_plate_pcd:  outline polyline w/ trapezoidal-ish notches → extrude    (med, sketch-first)
  with_hub:        notched_disc + back-side hub stub                        (med)
  with_hub_keyway: + DIN-style keyway                                       (hard)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("notched_disc", "thin_plate_pcd", "with_hub", "with_hub_keyway")


def _notched_outline(r_root, r_tip, z, gap_frac=0.4):
    """Outline polyline: tooth tip flats with curved gaps approximated as rect notch."""
    pts = []
    pitch = 2 * math.pi / z
    half_g = pitch * gap_frac / 2
    for i in range(z):
        c = i * pitch
        # Tooth crown: from c-half_t at tip to c+half_t at tip, then dip to root
        a_tooth_l = c - (pitch / 2 - half_g)
        a_tooth_r = c + (pitch / 2 - half_g)
        a_root_l = c + (pitch / 2 - half_g)  # transition
        a_root_r = c + pitch / 2
        for ang, r in [
            (a_tooth_l, r_tip),
            (a_tooth_r, r_tip),
            (a_root_l, r_root),
            (a_root_r, r_root),
        ]:
            pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    return pts


class SimpleSprocketFamily(BaseFamily):
    name = "simple_sprocket"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "notched_disc"
        elif difficulty == "medium":
            v = str(rng.choice(["thin_plate_pcd", "with_hub"]))
        else:
            v = str(rng.choice(["with_hub", "with_hub_keyway", "thin_plate_pcd"]))

        r = round(float(rng.uniform(15, 32)), 1)
        th = round(float(rng.uniform(3, 8)), 1)
        z = int(rng.choice([10, 12, 14, 16, 18, 20]))
        bore = round(float(rng.uniform(4, max(5, r * 0.4))), 1)
        tooth_h = round(r * float(rng.uniform(0.1, 0.18)), 2)
        p = {
            "variant": v,
            "radius": r,
            "thickness": th,
            "n_teeth": z,
            "bore_d": bore,
            "tooth_h": tooth_h,
            "difficulty": difficulty,
        }

        if v in ("with_hub", "with_hub_keyway"):
            p["hub_d"] = round(min(bore * float(rng.uniform(2.0, 2.8)), r * 0.85), 1)
            p["hub_h"] = round(th * float(rng.uniform(0.6, 1.4)), 1)

        if v == "with_hub_keyway":
            p["keyway_w"] = max(2.0, round(bore * 0.25, 1))
            p["keyway_h"] = round(p["keyway_w"] * 0.6, 2)

        return p

    def validate_params(self, p):
        if p["radius"] < 8 or p["thickness"] < 2:
            return False
        if p["bore_d"] >= p["radius"] * 1.4:
            return False
        if "hub_d" in p and p["hub_d"] >= p["radius"]:
            return False
        return True

    def make_program(self, p):
        v = p["variant"]
        r = p["radius"]
        th = p["thickness"]
        z = p["n_teeth"]
        bore = p["bore_d"]
        tooth_h = p["tooth_h"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        if v == "thin_plate_pcd":
            r_root = round(r - tooth_h, 3)
            r_tip = r
            pts = _notched_outline(r_root, r_tip, z)
            ops += [
                Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}),
                Op("polyline", {"points": pts[1:] + [pts[0]]}),
                Op("close", {}),
                Op("extrude", {"distance": th}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["thin_plate"] = True
        else:
            # Disc + polar-array rect notches (cut from rim inward)
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": th}),
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {
                        "radius": round(r + 0.1, 3),
                        "startAngle": 0,
                        "angle": 360,
                        "count": z,
                    },
                ),
                Op(
                    "rect",
                    {"length": tooth_h * 2.2, "width": 2 * math.pi * r / z * 0.42},
                ),
                Op("cutThruAll", {}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = z

        if "hub_d" in p:
            ops += [
                Op("workplane", {"selector": "<Z"}),
                Op("circle", {"radius": p["hub_d"] / 2}),
                Op("extrude", {"distance": p["hub_h"]}),
                Op("workplane", {"selector": "<Z"}),
                Op("hole", {"diameter": bore, "depth": p["hub_h"] + 1}),
            ]
            tags["has_hub"] = True

        if "keyway_w" in p:
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("center", {"x": 0.0, "y": round(bore / 2 + p["keyway_h"] / 2, 3)}),
                Op("rect", {"length": p["keyway_w"], "width": p["keyway_h"] + 1.0}),
                Op("cutThruAll", {}),
            ]
            tags["has_keyway"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
