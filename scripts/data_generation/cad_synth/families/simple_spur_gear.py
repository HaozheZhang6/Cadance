"""simple_spur_gear — non-ISO simplified gear focused on op-composition diversity.

NOT a real gear: replaces involute teeth with rectangular notches and exercises
many op patterns. Goal is op coverage (extrude + polarArray + cut + chamfer +
fillet + hole + sketch-first thin-plate) rather than mechanical fidelity.

Variants (cover different op-composition styles):
  bare_disc:      circle → extrude → bore                            (easy)
  cut_teeth:      disc → polarArray rect cut → bore                  (med/hard)
  thin_plate:     polyline (gear outline w/ square teeth) → extrude → bore (薄板 sketch-first)
  spoked:         disc → polarArray hole cuts (lightening) → bore    (med/hard)
  rim_step:       outer disc → cut inner ring → hub stub             (med/hard)
  keyway:         any of above + DIN-style keyway slot               (hard)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_disc", "cut_teeth", "thin_plate", "spoked", "rim_step")


def _square_tooth_outline(
    r_root: float, r_tip: float, z: int, tooth_frac: float = 0.45
):
    """CCW polyline of a circular outline crenellated with z square teeth.

    tooth_frac: angular fraction of each pitch occupied by tooth crown (0.3-0.6).
    Returns list of (x, y) tuples; caller closes the wire.
    """
    pts = []
    pitch = 2 * math.pi / z
    half_t = pitch * tooth_frac / 2
    for i in range(z):
        c = i * pitch
        # Simpler crenellation: gap (root) on left, tooth (tip) on right of pitch line
        a0 = c - pitch / 2  # gap start
        a1 = c - half_t  # tooth left edge (rise from root)
        a2 = c + half_t  # tooth right edge (fall to root)
        for ang, r in [
            (a0, r_root),
            (a1, r_root),
            (a1, r_tip),
            (a2, r_tip),
            (a2, r_root),
        ]:
            pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    return pts


class SimpleSpurGearFamily(BaseFamily):
    name = "simple_spur_gear"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        # Easy biased toward bare_disc; harder unlocks more variants.
        if difficulty == "easy":
            variant = str(rng.choice(["bare_disc", "bare_disc", "cut_teeth"]))
        elif difficulty == "medium":
            variant = str(rng.choice(["cut_teeth", "thin_plate", "spoked", "rim_step"]))
        else:  # hard
            variant = str(rng.choice(VARIANTS))

        r_pitch = round(float(rng.uniform(15, 40)), 1)
        thickness = round(float(rng.uniform(4, 12)), 1)
        bore_d = round(float(rng.uniform(4, max(5, r_pitch * 0.45))), 1)
        z = int(rng.integers(8, 24))
        tooth_h = round(r_pitch * float(rng.uniform(0.08, 0.18)), 2)

        p = {
            "variant": variant,
            "pitch_radius": r_pitch,
            "thickness": thickness,
            "bore_d": bore_d,
            "n_teeth": z,
            "tooth_height": tooth_h,
            "difficulty": difficulty,
        }

        if variant == "spoked":
            p["n_holes"] = int(rng.choice([4, 5, 6, 8]))
            p["hole_d"] = round(float(rng.uniform(2.0, max(2.1, r_pitch * 0.18))), 1)
            p["hole_pcd"] = round(r_pitch * float(rng.uniform(0.45, 0.7)), 1)

        if variant == "rim_step":
            p["inner_ring_r"] = round(r_pitch * float(rng.uniform(0.55, 0.78)), 1)
            p["hub_r"] = round(
                max(bore_d / 2 + 2.0, r_pitch * float(rng.uniform(0.18, 0.32))), 1
            )
            p["hub_h"] = round(thickness * float(rng.uniform(0.4, 0.8)), 1)

        if difficulty == "hard":
            if rng.uniform(0, 1) < 0.5:
                p["chamfer"] = round(min(thickness * 0.2, 0.8), 2)
            if rng.uniform(0, 1) < 0.5:
                kw = max(2.0, round(bore_d * 0.25, 1))
                p["keyway_w"] = kw
                p["keyway_h"] = round(kw * 0.6, 2)

        return p

    def validate_params(self, p: dict) -> bool:
        if p["pitch_radius"] < 8 or p["thickness"] < 2:
            return False
        if p["bore_d"] >= p["pitch_radius"] * 1.4 or p["bore_d"] < 2:
            return False
        if p["n_teeth"] < 6:
            return False
        if p["variant"] == "spoked":
            ring_in = p["bore_d"] / 2 + p["hole_d"] / 2 + 1
            ring_out = p["pitch_radius"] - p["hole_d"] / 2 - 1
            if p["hole_pcd"] < ring_in or p["hole_pcd"] > ring_out:
                return False
        if p["variant"] == "rim_step":
            if p["hub_r"] <= p["bore_d"] / 2 + 0.5:
                return False
            if p["inner_ring_r"] <= p["hub_r"] + 1.5:
                return False
        return True

    def make_program(self, p: dict) -> Program:
        v = p["variant"]
        r = p["pitch_radius"]
        th = p["thickness"]
        bore = p["bore_d"]
        z = p["n_teeth"]
        tooth_h = p["tooth_height"]

        ops: list = []
        tags = {"variant": v, "rotational": True, "has_hole": True}

        if v == "bare_disc":
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": th}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
        elif v == "cut_teeth":
            # Build solid disc then cut N rectangular teeth in polar array.
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": th}),
            ]
            tooth_w = round(2 * math.pi * r / z * 0.45, 3)
            cutter_l = round(tooth_h * 2.2, 3)  # over-deep
            ops += [
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
                Op("rect", {"length": cutter_l, "width": tooth_w}),
                Op("cutThruAll", {}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = z
        elif v == "thin_plate":
            # Sketch-first: build full crenellated outline polyline + single extrude.
            r_root = round(r - tooth_h * 0.5, 3)
            r_tip = round(r + tooth_h * 0.5, 3)
            pts = _square_tooth_outline(r_root, r_tip, z, tooth_frac=0.5)
            ops += [
                Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}),
                Op("polyline", {"points": pts[1:] + [pts[0]]}),
                Op("close", {}),
                Op("extrude", {"distance": th}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["thin_plate"] = True
        elif v == "spoked":
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": th}),
                Op("workplane", {"selector": ">Z"}),
                Op(
                    "polarArray",
                    {
                        "radius": p["hole_pcd"],
                        "startAngle": 0,
                        "angle": 360,
                        "count": p["n_holes"],
                    },
                ),
                Op("hole", {"diameter": p["hole_d"]}),
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]
            tags["polar_array"] = p["n_holes"]
        else:  # rim_step
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": th}),
                # Cut annular pocket: ring(inner, hub_r) from top
                Op("workplane", {"selector": ">Z"}),
                Op("circle", {"radius": p["inner_ring_r"]}),
                Op("circle", {"radius": p["hub_r"]}),
                Op("cutBlind", {"depth": round(th - p["hub_h"], 3)}),
                # Bore through
                Op("workplane", {"selector": ">Z"}),
                Op("hole", {"diameter": bore}),
            ]

        # Optional features
        if "chamfer" in p:
            ops += [
                Op("edges", {"selector": ">Z"}),
                Op("chamfer", {"length": p["chamfer"]}),
            ]
            tags["has_chamfer"] = True

        if "keyway_w" in p:
            kw = p["keyway_w"]
            kh = p["keyway_h"]
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("center", {"x": 0.0, "y": round(bore / 2 + kh / 2, 3)}),
                Op("rect", {"length": kw, "width": round(kh + 1.0, 3)}),
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
