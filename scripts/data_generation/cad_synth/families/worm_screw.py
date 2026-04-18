"""Worm screw — ZA-profile (Archimedean) stepped worm per ISO 10828.

Rewritten from: tmp/manual_family_previews/manual_worm_screw.py

Construction (matches manual logic):
  1. Shaft: circle(df/2).extrude(sl) — shifted so thread ends up centered.
     Manual: circle+extrude from z=0 to z=sl, then translate thread by z_off.
     Here: shift shaft downward by z_off via transformed, so shaft spans
     z=[-z_off, sl-z_off]. Thread at z≈[-bw/2, tl+bw/2] ends up centered.
  2. Thread: XZ-plane trapezoidal profile at center(df/2, 0),
     swept along helix(lead, tl, df/2).
     Op-system: union sub-op with base_plane flipped to XZ so that
     center(df/2, 0) matches the manual exactly.
  3. End chamfers on shaft circular edges (medium+)

Note: In the Op system, translate-after-sweep is not available. We center
the thread on the shaft by shifting the SHAFT down by z_off=(sl-tl)/2
(equivalent to translating the thread up by z_off).

Easy:   stepped shaft + single-start thread
Medium: + multi-start (z1∈{1,2}) + end chamfers
Hard:   + bore hole + keyway
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program

_MODULE_SERIES = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.15, 4.0, 5.0, 6.0, 6.3, 8.0, 10.0]


class WormScrewFamily(BaseFamily):
    name = "worm_screw"

    def sample_params(self, difficulty: str, rng) -> dict:
        m = float(rng.choice(_MODULE_SERIES[:8]))
        # z1 restricted to {1, 2} — standard worm (z1=4 rarely used; sweep
        # with high lead + short thread_length can produce non-manifold geom)
        z1 = 1 if difficulty == "easy" else int(rng.choice([1, 2]))
        q = rng.uniform(7, 14)
        d1 = round(m * q, 1)
        alpha = 20.0

        z2 = int(rng.choice([20, 25, 30, 40, 50, 60, 80]))
        thread_length = round((11 + 0.06 * z2) * m, 1)
        shaft_length = round(thread_length + rng.uniform(m * 8, m * 16), 1)

        params = {
            "module": m,
            "z1": z1,
            "d1": d1,
            "alpha": alpha,
            "z2": z2,
            "thread_length": thread_length,
            "shaft_length": shaft_length,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(rng.uniform(0.5, max(0.6, m * 0.6)), 1)

        if difficulty == "hard":
            df = d1 - 2 * 1.2 * m
            bore_d = round(df * rng.uniform(0.25, 0.45), 1)
            params["bore_diameter"] = bore_d
            kw = round(bore_d * rng.uniform(0.3, 0.5), 1)
            params["keyway_width"] = kw

        params["base_plane"] = "XY"
        return params

    def validate_params(self, params: dict) -> bool:
        m = params["module"]
        d1 = params["d1"]
        tl = params["thread_length"]
        sl = params["shaft_length"]

        hf = 1.2 * m
        df = d1 - 2 * hf
        if df < 4:
            return False
        if tl >= sl:
            return False
        if tl < 5 or sl > 600:
            return False

        bd = params.get("bore_diameter")
        if bd and bd >= df * 0.6:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        m = params["module"]
        z1 = params["z1"]
        d1 = params["d1"]
        alpha = params["alpha"]
        tl = params["thread_length"]
        sl = params["shaft_length"]

        # Derived (ISO 10828)
        p = round(math.pi * m, 4)
        lead = round(p * z1, 4)
        ha = m
        hf = round(1.2 * m, 4)
        df = round(d1 - 2 * hf, 3)
        tooth_thickness = round(p / 2, 4)
        top_width = round(
            tooth_thickness - 2 * ha * math.tan(math.radians(alpha)), 4
        )
        bottom_width = round(
            tooth_thickness + 2 * hf * math.tan(math.radians(alpha)), 4
        )
        tooth_height = round(ha + hf, 3)

        bw2 = round(bottom_width / 2, 3)
        tw2 = round(top_width / 2, 3)
        th = round(tooth_height, 3)
        profile_pts = [
            [0.0, round(-bw2, 3)],
            [th, round(-tw2, 3)],
            [th, round(tw2, 3)],
            [0.0, round(bw2, 3)],
        ]

        # z_off centers thread on shaft (matches manual's post-translate)
        z_off = round((sl - tl) / 2, 3)

        ops = []
        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # ── 1. Shaft: circle.extrude, shifted down by z_off ──
        # Manual: Workplane('XY').circle(df/2).extrude(sl)  [z=0..sl]
        # Here we pre-shift the workplane so shaft ends up centered around
        # the thread (which naturally spans z≈[-bw/2, tl+bw/2]).
        ops.append(
            Op(
                "transformed",
                {"offset": [0.0, 0.0, -z_off], "rotate": [0.0, 0.0, 0.0]},
            )
        )
        ops.append(Op("circle", {"radius": round(df / 2, 3)}))
        ops.append(Op("extrude", {"distance": round(sl, 3)}))

        # ── 2. Thread: XZ-plane profile swept along helix ──
        # Manual: Workplane('XZ').center(df/2, 0).polyline([...]).close()
        #         .sweep(makeHelix(lead, tl, df/2), isFrenet=True)
        # Op-system: union sub-op. Sub starts from Workplane('XY'),
        # we rotate to XZ-equivalent via transformed(rotate=[90,0,0])
        # so local X=world X (radial), local Y=world Z (axial).
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, 0.0, 0.0],
                                "rotate": [90.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "center",
                            "args": {"x": round(df / 2, 3), "y": 0.0},
                        },
                        {"name": "polyline", "args": {"points": profile_pts}},
                        {"name": "close"},
                        {
                            "name": "sweep",
                            "args": {
                                "path_type": "helix",
                                "path_args": {
                                    "pitch": round(lead, 3),
                                    "height": round(tl, 3),
                                    "radius": round(df / 2, 3),
                                },
                                "isFrenet": True,
                            },
                        },
                    ]
                },
            )
        )

        # ── 3. End chamfers (medium+) ──
        cl = params.get("chamfer")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": round(cl, 3)}))
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": round(cl, 3)}))

        # ── 4. Bore (hard) ──
        bd = params.get("bore_diameter")
        if bd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": round(bd, 3)}))

        # ── 5. Keyway (hard) ──
        kw = params.get("keyway_width")
        if kw and bd:
            tags["has_slot"] = True
            kh = round(kw * 0.6, 2)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op("pushPoints", {"points": [(0.0, round(bd / 2, 3))]})
            )
            ops.append(Op("rect", {"length": round(kw, 3), "width": kh}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
