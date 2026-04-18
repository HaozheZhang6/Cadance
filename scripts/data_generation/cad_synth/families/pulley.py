"""Pulley / belt sheave — revolved cross-section profile.

Structural type: 2D polyline profile revolved 360° around Y axis.
Covers: V-belt pulley, flat-belt pulley, timing pulley.

Easy:   flat-belt pulley (cylindrical rim) revolved
Medium: + V-groove + hub bore
Hard:   + spoked body (lightening cut pockets) + keyway
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program


class PulleyFamily(BaseFamily):
    name = "pulley"

    def sample_params(self, difficulty: str, rng) -> dict:
        rim_r = rng.uniform(15, 80)      # outer rim radius
        width = rng.uniform(10, 50)      # total axial width
        bore_r = rng.uniform(4, max(4.1, rim_r * 0.25))   # shaft bore radius
        hub_r = rng.uniform(bore_r + 3, max(bore_r + 3.5, rim_r * 0.45))
        rim_t = rng.uniform(3, max(3.1, min(10, width * 0.25)))   # rim wall thickness

        params = {
            "rim_radius": round(rim_r, 1),
            "width": round(width, 1),
            "bore_radius": round(bore_r, 1),
            "hub_radius": round(hub_r, 1),
            "rim_thickness": round(rim_t, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            groove_d = rng.uniform(rim_t * 0.25, max(rim_t * 0.26, rim_t * 0.65))
            # ISO 22 / ISO 4183 standard groove angles: 34°, 36°, 38°
            groove_angle = float(rng.choice([34.0, 36.0, 38.0]))
            params["groove_depth"] = round(groove_d, 1)
            params["groove_angle"] = groove_angle

        if difficulty == "hard":
            n_spokes = int(rng.choice([4, 6]))
            spoke_w = rng.uniform(4, max(4.1, min(12, (rim_r - hub_r) * 0.3)))
            params["n_spokes"] = n_spokes
            params["spoke_width"] = round(spoke_w, 1)
            kw = rng.uniform(bore_r * 0.4, max(bore_r * 0.41, bore_r * 0.65))
            params["keyway_width"] = round(kw, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        rr = params["rim_radius"]
        w = params["width"]
        br = params["bore_radius"]
        hr = params["hub_radius"]
        rt = params["rim_thickness"]

        if br >= hr or hr >= rr * 0.6:
            return False
        if rt >= w * 0.4 or rr < 10:
            return False

        gd = params.get("groove_depth")
        if gd and gd >= rt * 0.9:
            return False

        sw = params.get("spoke_width")
        if sw and sw >= (rr - hr) * 0.45:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rr = params["rim_radius"]
        w = params["width"]
        br = params["bore_radius"]
        hr = params["hub_radius"]
        rt = params["rim_thickness"]

        ops, tags = [], {
            "has_hole": True, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": True,
        }

        gd = params.get("groove_depth", 0)
        ga = params.get("groove_angle", 38)

        # Build 2D cross-section profile in XY plane (X = radial, Y = axial).
        # Profile is the half cross-section (x >= 0), revolved around Y axis.
        # Ordered: inner bore surface → web → rim → revolve.

        w2 = w / 2  # half-width
        hub_web_r = hr  # outer edge of hub/web

        if gd > 0:
            # V-groove pulley: rim has a groove cut in the middle
            groove_half_w = round(gd / math.tan(math.radians(ga)), 3)
            pts = [
                # Inner bore bottom
                [round(br, 3), round(-w2, 3)],
                # Hub outer edge bottom
                [round(hub_web_r, 3), round(-w2, 3)],
                # Web (straight out to rim inner)
                [round(rr - rt, 3), round(-w2, 3)],
                # Rim inner bottom
                [round(rr - rt, 3), round(-w2 + rt, 3)],
                # Rim outer bottom flange
                [round(rr, 3), round(-w2 + rt, 3)],
                # V-groove left flank
                [round(rr, 3), round(-groove_half_w, 3)],
                [round(rr - gd, 3), 0.0],
                [round(rr, 3), round(groove_half_w, 3)],
                # Rim outer top flange
                [round(rr, 3), round(w2 - rt, 3)],
                # Rim inner top
                [round(rr - rt, 3), round(w2 - rt, 3)],
                [round(rr - rt, 3), round(w2, 3)],
                # Hub outer edge top
                [round(hub_web_r, 3), round(w2, 3)],
                # Inner bore top
                [round(br, 3), round(w2, 3)],
            ]
            tags["has_slot"] = True
        else:
            # Flat-belt pulley: simple cylindrical rim
            pts = [
                [round(br, 3), round(-w2, 3)],
                [round(hub_web_r, 3), round(-w2, 3)],
                [round(rr - rt, 3), round(-w2, 3)],
                [round(rr - rt, 3), round(-w2 + rt, 3)],
                [round(rr, 3), round(-w2 + rt, 3)],
                [round(rr, 3), round(w2 - rt, 3)],
                [round(rr - rt, 3), round(w2 - rt, 3)],
                [round(rr - rt, 3), round(w2, 3)],
                [round(hub_web_r, 3), round(w2, 3)],
                [round(br, 3), round(w2, 3)],
            ]

        ops.append(Op("polyline", {"points": pts}))
        ops.append(Op("close", {}))
        ops.append(Op("revolve", {
            "angleDeg": 360,
            "axisStart": [0, 0, 0],
            "axisEnd": [0, 1, 0],
        }))

        # Spoked body — polar array of rectangular cutout pockets (hard)
        n_sp = params.get("n_spokes")
        sw = params.get("spoke_width")
        if n_sp and sw:
            pocket_r = round((hr + rr - rt) / 2, 3)
            pocket_l = round(rr - rt - hr - 4, 3)
            pocket_h = round(w - 4, 3)
            for i in range(n_sp):
                angle_deg = round(360.0 * i / n_sp, 3)
                ops.append(Op("cut", {"ops": [
                    {"name": "transformed", "args": {
                        "offset": [pocket_r, 0.0, 0.0],
                        "rotate": [0.0, 0.0, angle_deg],
                    }},
                    {"name": "box", "args": {
                        "length": pocket_l,
                        "width": sw,
                        "height": pocket_h * 2,
                        "centered": True,
                    }},
                ]}))

        # Keyway (hard)
        kw = params.get("keyway_width")
        if kw:
            tags["has_slot"] = True
            kh = round(kw * 0.6, 2)
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("pushPoints", {"points": [(0.0, round(br, 3))]}))
            ops.append(Op("rect", {"length": kw, "width": kh}))
            ops.append(Op("cutThruAll", {}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
