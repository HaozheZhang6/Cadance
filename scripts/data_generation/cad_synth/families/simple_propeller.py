"""simple_propeller — central hub + N flat rectangular blades.

Variants:
  bare_hub:           short cylinder with through bore                  (easy)
  flat_blades:        hub + N flat rectangular blades                   (med)
  twisted_blades:     hub + N blades extruded with small twist          (hard)
  thin_plate_prop:    hub + petal outline blades single extrude         (hard, sketch-first)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_hub", "flat_blades", "twisted_blades", "thin_plate_prop")


def _petal_outline(r_hub, r_tip, n):
    """Closed petal outline: each blade contributes 4 unique pts; root pts shared between blades."""
    pts = []
    pitch = 2 * math.pi / n
    bf = 0.25
    for i in range(n):
        c = i * pitch
        # 4 pts per blade; the trailing root point coincides with next blade's leading root
        for ang, r in [
            (c - pitch / 2, r_hub),
            (c - bf * pitch / 2, r_hub),
            (c - bf * pitch / 2, r_tip),
            (c + bf * pitch / 2, r_tip),
            (c + bf * pitch / 2, r_hub),
        ]:
            pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    # Dedupe consecutive coincident points (numerical noise around blade gaps)
    out = [pts[0]]
    for q in pts[1:]:
        if abs(q[0] - out[-1][0]) > 1e-3 or abs(q[1] - out[-1][1]) > 1e-3:
            out.append(q)
    return out


class SimplePropellerFamily(BaseFamily):
    name = "simple_propeller"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_hub"
        elif difficulty == "medium":
            v = "flat_blades"
        else:
            v = str(rng.choice(VARIANTS[1:]))

        rh = round(float(rng.uniform(6, 14)), 1)
        hh = round(float(rng.uniform(8, 20)), 1)
        n = int(rng.choice([2, 3, 4, 5]))
        rt = round(rh + float(rng.uniform(15, 40)), 1)
        bw = round(float(rng.uniform(2.5, 5)), 1)
        bh = round(hh * float(rng.uniform(0.25, 0.55)), 1)
        bore = round(float(rng.uniform(3, max(4, rh * 0.55))), 1)
        # Avoid twist=0 — cadquery twistExtrude divides by angle internally
        twist = float(rng.choice([15, 20, 25, 35, 45]))
        return {
            "variant": v,
            "r_hub": rh,
            "h_hub": hh,
            "n_blade": n,
            "r_tip": rt,
            "blade_w": bw,
            "blade_h": bh,
            "bore_d": bore,
            "twist_deg": twist,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_hub"] >= 4
            and p["r_tip"] > p["r_hub"] + 5
            and p["bore_d"] < p["r_hub"] * 1.7
            and p["h_hub"] >= 4
        )

    def make_program(self, p):
        v = p["variant"]
        rh, hh, n = p["r_hub"], p["h_hub"], p["n_blade"]
        rt = p["r_tip"]
        bw = p["blade_w"]
        bh_ = p["blade_h"]
        bore = p["bore_d"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        # Hub (cylinder)
        ops += [Op("circle", {"radius": rh}), Op("extrude", {"distance": hh})]

        if v == "bare_hub":
            ops += [Op("workplane", {"selector": ">Z"}), Op("hole", {"diameter": bore})]
        elif v == "flat_blades":
            blade_len = round(rt - rh + 1, 2)
            mid_z = round(hh * 0.4, 2)
            ops += [
                Op("workplane_offset", {"offset": mid_z}),
                Op(
                    "polarArray",
                    {
                        "radius": (rh + rt) / 2,
                        "startAngle": 0,
                        "angle": 360,
                        "count": n,
                    },
                ),
                Op("rect", {"length": blade_len, "width": bw}),
                Op("extrude", {"distance": bh_}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = n
        elif v == "twisted_blades":
            blade_len = round(rt - rh + 1, 2)
            mid_z = round(hh * 0.3, 2)
            tw = p["twist_deg"]
            ops += [
                Op("workplane_offset", {"offset": mid_z}),
                Op(
                    "polarArray",
                    {
                        "radius": (rh + rt) / 2,
                        "startAngle": 0,
                        "angle": 360,
                        "count": n,
                    },
                ),
                Op("rect", {"length": blade_len, "width": bw}),
                Op("twistExtrude", {"distance": bh_, "angle": tw}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = n
            tags["twist_deg"] = tw
        else:  # thin_plate_prop — petal outline single extrude + hub bore
            pts = _petal_outline(rh, rt, n)
            ops += [
                Op("workplane_offset", {"offset": round(hh * 0.4, 2)}),
                Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}),
                Op("polyline", {"points": pts[1:] + [pts[0]]}),
                Op("close", {}),
                Op("extrude", {"distance": bh_}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["thin_plate"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
