"""Cam — eccentric or lobe disc profile polyline + extrude.

Structural type: off-center or lobed 2D profile → polyline → extrude.
Covers: eccentric cams, lobe cams, engine cams.
Topologically different from all other families: irregular non-circular disc.

Easy:   eccentric circular disc (offset circle profile) + shaft bore
Medium: + lobe bump (raised region on profile) + keyway
Hard:   + second lobe at 180° + oil hole
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


def _eccentric_pts(r, e, n=48):
    """Circle of radius r offset by e from origin — eccentric cam profile."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = r * math.cos(a) + e
        y = r * math.sin(a)
        pts.append((round(x, 3), round(y, 3)))
    return pts


def _lobe_pts(r_base, lobe_h, lobe_angle_deg, lobe_half_width_deg=40, n=64):
    """Base circle with a raised lobe at lobe_angle_deg."""
    la = math.radians(lobe_angle_deg)
    lhw = math.radians(lobe_half_width_deg)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        # Gaussian lobe bump
        da = a - la
        # wrap to [-pi, pi]
        while da > math.pi:
            da -= 2 * math.pi
        while da < -math.pi:
            da += 2 * math.pi
        bump = lobe_h * math.exp(-0.5 * (da / (lhw / 2)) ** 2)
        r = r_base + bump
        pts.append((round(r * math.cos(a), 3), round(r * math.sin(a), 3)))
    return pts


class CamFamily(BaseFamily):
    name = "cam"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        r_base = rng.uniform(10, 40)
        eccentricity = rng.uniform(r_base * 0.1, max(r_base * 0.11, r_base * 0.4))
        thickness = rng.uniform(8, 30)
        bore_d = rng.uniform(4, max(4.1, r_base * 0.4))

        params = {
            "base_radius": round(r_base, 1),
            "eccentricity": round(eccentricity, 1),
            "thickness": round(thickness, 1),
            "bore_diameter": round(bore_d, 1),
            "difficulty": difficulty,
        }

        # Hub boss always present — helps cam read as driven machine element
        hub_r = round(bore_d / 2 * rng.uniform(1.8, 2.6), 1)
        hub_h = round(rng.uniform(thickness * 0.35, thickness * 0.65), 1)
        params["hub_radius"] = hub_r
        params["hub_height"] = hub_h

        if difficulty in ("medium", "hard"):
            lobe_h = round(
                rng.uniform(r_base * 0.1, max(r_base * 0.11, r_base * 0.35)), 1
            )
            lobe_angle = round(rng.uniform(0, 360), 1)
            params["lobe_height"] = lobe_h
            params["lobe_angle"] = lobe_angle
            kw = round(
                max(1.5, rng.uniform(bore_d * 0.30, max(bore_d * 0.31, bore_d * 0.5))),
                1,
            )
            params["keyway_width"] = kw

        if difficulty == "hard":
            # Second lobe at 180°
            lobe2_h = round(
                rng.uniform(
                    params["lobe_height"] * 0.4,
                    max(params["lobe_height"] * 0.41, params["lobe_height"] * 0.8),
                ),
                1,
            )
            params["lobe2_height"] = lobe2_h
            params["lobe2_angle"] = round((params["lobe_angle"] + 180) % 360, 1)
            params["oil_hole_diameter"] = round(
                rng.uniform(1.5, max(1.6, min(5.0, bore_d * 0.4))), 1
            )

        return params

    def validate_params(self, params: dict) -> bool:
        rb = params["base_radius"]
        e = params["eccentricity"]
        bd = params["bore_diameter"]

        if e >= rb * 0.5 or bd >= rb * 0.6:
            return False

        hr = params.get("hub_radius")
        if hr and hr >= rb * 0.7:
            return False

        lh = params.get("lobe_height")
        if lh and lh >= rb * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rb = params["base_radius"]
        e = params["eccentricity"]
        thick = params["thickness"]
        bd = params["bore_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        lh = params.get("lobe_height")
        la = params.get("lobe_angle", 0)
        lh2 = params.get("lobe2_height")
        la2 = params.get("lobe2_angle", 180)

        if lh:
            # Lobe cam profile
            if lh2:
                # Two lobes: compute composite profile
                pts_base = _lobe_pts(rb, lh, la, lobe_half_width_deg=35, n=64)
                # Add second lobe as additional bump
                la2_rad = math.radians(la2)
                lhw = math.radians(35)
                la_rad = math.radians(la)
                final_pts = []
                n = 64
                for i in range(n):
                    a = 2 * math.pi * i / n
                    # lobe 1
                    da1 = a - la_rad
                    while da1 > math.pi:
                        da1 -= 2 * math.pi
                    while da1 < -math.pi:
                        da1 += 2 * math.pi
                    b1 = lh * math.exp(-0.5 * (da1 / (lhw / 2)) ** 2)
                    # lobe 2
                    da2 = a - la2_rad
                    while da2 > math.pi:
                        da2 -= 2 * math.pi
                    while da2 < -math.pi:
                        da2 += 2 * math.pi
                    b2 = lh2 * math.exp(-0.5 * (da2 / (lhw / 2)) ** 2)
                    r = rb + b1 + b2
                    final_pts.append(
                        (round(r * math.cos(a), 3), round(r * math.sin(a), 3))
                    )
                pts = final_pts
            else:
                pts = _lobe_pts(rb, lh, la, n=64)
        else:
            # Eccentric disc
            pts = _eccentric_pts(rb, e, n=48)

        ops.append(Op("polyline", {"points": pts}))
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": thick}))

        # Hub boss — raised cylinder at center (drive/bearing seat)
        hub_r = params.get("hub_radius")
        hub_h = params.get("hub_height")
        if hub_r and hub_h:
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(thick + hub_h / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(hub_h, 3),
                                    "radius": round(hub_r, 3),
                                },
                            },
                        ]
                    },
                )
            )

        # Shaft bore through disc + hub
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": bd}))

        # Keyway (medium+)
        kw = params.get("keyway_width")
        if kw:
            tags["has_slot"] = True
            kh = round(kw * 0.6, 2)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(0.0, round(bd / 2, 3))]}))
            ops.append(Op("rect", {"length": kw, "width": kh}))
            ops.append(Op("cutThruAll", {}))

        # Oil/timing hole on disc face (hard)
        ohd = params.get("oil_hole_diameter")
        if ohd:
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [
                                        round(rb * 0.5, 3),
                                        0.0,
                                        round(thick / 2, 3),
                                    ],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(thick * 2, 3),
                                    "radius": round(ohd / 2, 3),
                                },
                            },
                        ]
                    },
                )
            )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
