"""Pulley / belt sheave — revolved cross-section profile (ISO 22 / ISO 4183).

ISO 22: Classical V-belt pulleys — groove angle α = 34°/36°/38° depending on PD.
ISO 4183: groove geometry per belt section (Z, A, B, C, D).

Belt section determines groove width and depth; pulley PD is continuously sampled.
Groove angle: 34° for small PD, 36° mid, 38° large (per ISO 22 Table 1).

Belt section table: (section, groove_width_mm, groove_depth_mm, pd_min_mm)

Reference: ISO 22:1991 — Classical V-belt pulleys — groove angles per PD
  ISO 4183:1989 — V-belt groove geometry; Table (Z/A/B/C/D groove_w, groove_d, pd_min)
  ISO 22 Table 1 preferred pitch diameters per belt section
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily, din6885a_keyway

# ISO 4183 V-belt groove geometry — (section, groove_width_mm, groove_depth_mm, pd_min_mm)
_ISO4183_BELT = [
    ("Z", 8.5, 7.0, 50),
    ("A", 11.0, 8.7, 75),
    ("B", 14.0, 10.8, 125),
    ("C", 19.0, 14.3, 200),
    ("D", 27.0, 19.9, 355),
]

# ISO 22 preferred pitch diameters (mm) per belt section
_ISO22_PD = {
    "Z": [50, 56, 63, 71, 80, 90, 100, 112, 125],
    "A": [75, 80, 90, 100, 112, 125, 140, 160, 180, 200],
    "B": [125, 140, 160, 180, 200, 224, 250],
    "C": [200, 224, 250, 280, 315, 355],
    "D": [355, 400, 450, 500],
}


class PulleyFamily(BaseFamily):
    name = "pulley"
    standard = "ISO 22"

    def sample_params(self, difficulty: str, rng) -> dict:
        # Anchor on ISO 4183 belt section first, then derive geometry
        if difficulty == "easy":
            belt_pool = _ISO4183_BELT[:3]   # Z, A, B
        elif difficulty == "medium":
            belt_pool = _ISO4183_BELT[:4]   # Z, A, B, C
        else:
            belt_pool = _ISO4183_BELT       # all sections

        belt_section, groove_w, groove_depth_std, pd_min = belt_pool[
            int(rng.integers(0, len(belt_pool)))
        ]

        # ISO 22 preferred pitch diameter
        pd_opts = _ISO22_PD[belt_section]
        pd_mm = float(pd_opts[int(rng.integers(0, len(pd_opts)))])
        rim_r = round(pd_mm / 2, 1)

        # Rim thickness: must contain groove depth with margin
        rim_t = round(groove_depth_std * float(rng.choice([1.3, 1.5, 1.8, 2.0])), 1)

        # Total axial width: groove width + two flanges (3–8 mm each side)
        flange = float(rng.choice([3.0, 4.0, 5.0, 6.0, 8.0]))
        width = round(groove_w + 2.0 * flange, 1)

        # Bore: 15–25% of rim radius; hub: capped at 50% of rim radius
        bore_r = round(rim_r * float(rng.choice([0.15, 0.18, 0.20, 0.25])), 1)
        bore_r = max(bore_r, 4.0)
        hub_r_raw = round(bore_r * float(rng.choice([1.6, 1.8, 2.0, 2.2])), 1)
        hub_r = min(hub_r_raw, round(rim_r * 0.50, 1))

        # Rim thickness must be < 35% of width to pass validate
        rim_t = round(min(groove_depth_std * float(rng.choice([1.3, 1.5, 1.8])), width * 0.30), 1)
        rim_t = max(rim_t, 3.0)

        # ISO 22: groove angle by pitch diameter
        if pd_mm < 100:
            groove_angle = 34.0
        elif pd_mm < 200:
            groove_angle = 36.0
        else:
            groove_angle = 38.0

        params = {
            "belt_section": belt_section,
            "rim_radius": rim_r,
            "width": width,
            "bore_radius": bore_r,
            "hub_radius": hub_r,
            "rim_thickness": rim_t,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            groove_d = round(min(groove_depth_std, rim_t * 0.65), 1)
            params["groove_depth"] = groove_d
            params["groove_angle"] = groove_angle

        if difficulty == "hard":
            n_spokes = int(rng.choice([4, 6]))
            spoke_w = round(float(rng.choice([6.0, 8.0, 10.0, 12.0])), 1)
            params["n_spokes"] = n_spokes
            params["spoke_width"] = spoke_w
            kw, kh = din6885a_keyway(bore_r * 2)
            params["keyway_width"] = kw
            params["keyway_height"] = kh

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
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
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
        ops.append(
            Op(
                "revolve",
                {
                    "angleDeg": 360,
                    "axisStart": [0, 0, 0],
                    "axisEnd": [0, 1, 0],
                },
            )
        )

        # Spoked body — polar array of rectangular cutout pockets (hard)
        n_sp = params.get("n_spokes")
        sw = params.get("spoke_width")
        if n_sp and sw:
            pocket_r = round((hr + rr - rt) / 2, 3)
            pocket_l = round(rr - rt - hr - 4, 3)
            pocket_h = round(w - 4, 3)
            for i in range(n_sp):
                angle_deg = round(360.0 * i / n_sp, 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [pocket_r, 0.0, 0.0],
                                        "rotate": [0.0, 0.0, angle_deg],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": pocket_l,
                                        "width": sw,
                                        "height": pocket_h * 2,
                                        "centered": True,
                                    },
                                },
                            ]
                        },
                    )
                )

        # Keyway (hard) — DIN 6885A dimensions from params
        kw = params.get("keyway_width")
        kh = params.get("keyway_height")
        if kw and kh:
            tags["has_slot"] = True
            ops.append(Op("workplane", {"selector": ">Y"}))
            ops.append(Op("pushPoints", {"points": [(0.0, round(br, 3))]}))
            ops.append(Op("rect", {"length": kw, "width": kh}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
