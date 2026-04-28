"""simple_impeller — disc + N rectangular blades unioned (no curved blades).

Variants:
  bare_hub:        disc + central bore                                       (easy)
  rect_blades:     disc + N rect-box blades unioned in polar array           (med)
  rect_blades_tilt: blades rotated slightly off-axial                        (hard)
  thin_plate_imp:  petal-shaped polyline outline → extrude → bore            (hard, sketch-first)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_hub", "rect_blades", "rect_blades_tilt", "thin_plate_imp")


def _petal_outline(r_hub, r_tip, n_blade):
    """Star-petal outline; emits 5 unique pts per blade then dedupes coincident pts."""
    pts = []
    pitch = 2 * math.pi / n_blade
    blade_frac = 0.35
    for i in range(n_blade):
        c = i * pitch
        a_root_l = c - pitch / 2
        a_blade_l = c - blade_frac * pitch / 2
        a_blade_r = c + blade_frac * pitch / 2
        for ang, r in [
            (a_root_l, r_hub),
            (a_blade_l, r_hub),
            (a_blade_l, r_tip),
            (a_blade_r, r_tip),
            (a_blade_r, r_hub),
        ]:
            pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    out = [pts[0]]
    for q in pts[1:]:
        if abs(q[0] - out[-1][0]) > 1e-3 or abs(q[1] - out[-1][1]) > 1e-3:
            out.append(q)
    return out


class SimpleImpellerFamily(BaseFamily):
    name = "simple_impeller"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_hub"
        elif difficulty == "medium":
            v = str(rng.choice(["rect_blades", "rect_blades"]))
        else:
            v = str(rng.choice(VARIANTS))

        r_hub = round(float(rng.uniform(8, 18)), 1)
        h_hub = round(float(rng.uniform(8, 22)), 1)
        n_blade = int(rng.choice([3, 4, 5, 6, 8]))
        r_tip = round(r_hub + float(rng.uniform(8, 22)), 1)
        blade_w = round(float(rng.uniform(2, 4)), 1)
        blade_h = round(h_hub * float(rng.uniform(0.5, 0.95)), 1)
        bore = round(float(rng.uniform(3, max(4, r_hub * 0.5))), 1)
        return {
            "variant": v,
            "r_hub": r_hub,
            "h_hub": h_hub,
            "n_blade": n_blade,
            "r_tip": r_tip,
            "blade_w": blade_w,
            "blade_h": blade_h,
            "bore_d": bore,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_hub"] >= 5
            and p["r_tip"] > p["r_hub"] + 3
            and p["bore_d"] < p["r_hub"] * 1.6
            and p["h_hub"] >= 4
        )

    def make_program(self, p):
        v = p["variant"]
        rh, hh, nb = p["r_hub"], p["h_hub"], p["n_blade"]
        rt = p["r_tip"]
        bw = p["blade_w"]
        bh_ = p["blade_h"]
        bore = p["bore_d"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        if v == "bare_hub":
            ops += [
                Op("circle", {"radius": rh}),
                Op("extrude", {"distance": hh}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
        elif v == "thin_plate_imp":
            pts = _petal_outline(rh, rt, nb)
            ops += [
                Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}),
                Op("polyline", {"points": pts[1:] + [pts[0]]}),
                Op("close", {}),
                Op("extrude", {"distance": bh_}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["thin_plate"] = True
        else:
            # rect_blades: hub + N radial rect boxes
            ops += [Op("circle", {"radius": rh}), Op("extrude", {"distance": hh})]
            blade_len = round(rt - rh + 1, 2)
            ops += [
                Op("workplane", {"selector": "<Z"}),
                Op(
                    "polarArray",
                    {
                        "radius": (rh + rt) / 2,
                        "startAngle": 0,
                        "angle": 360,
                        "count": nb,
                    },
                ),
                Op("rect", {"length": blade_len, "width": bw}),
                Op("extrude", {"distance": bh_}),
            ]
            ops += [Op("workplane", {"selector": ">Z"}), Op("hole", {"diameter": bore})]
            tags["polar_array"] = nb

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
