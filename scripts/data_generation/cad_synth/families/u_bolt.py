"""U-bolt — DIN 3570 round-bar pipe clamp.

180° bend joining two parallel threaded legs. Sized to pipe nominal diameter
(DN) per DIN 3570 Tab.1 — center distance e = pipe OD + rod dia + clearance.

Easy:   plain bent rod (no thread, no backing plate).
Medium: + welded backing saddle (solid plate fused to leg tips, no holes —
        holes are skipped to keep plate + bolt as one connected solid).
Hard:   + hex nut welded onto each leg tip (DIN 934 style hex prism,
        fused to the leg cylinder — simulates factory-assembled clamp).

Reference: DIN 3570:2021 — U-bolts for steel tube clamps; Tab.1 (DN, d, e, r).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 3570 Tab.1 (partial) — (DN_label, rod_d, center_dist_e, bend_r, leg_L)
_DIN3570 = [
    ("DN20", 8.0, 32.0, 16.0, 40.0),
    ("DN25", 8.0, 38.0, 19.0, 45.0),
    ("DN32", 10.0, 48.0, 24.0, 55.0),
    ("DN40", 10.0, 55.0, 27.5, 60.0),
    ("DN50", 12.0, 70.0, 35.0, 70.0),
    ("DN65", 12.0, 85.0, 42.5, 80.0),
    ("DN80", 16.0, 100.0, 50.0, 95.0),
    ("DN100", 16.0, 124.0, 62.0, 110.0),
]

_ISO261_PITCH = {8: 1.25, 10: 1.5, 12: 1.75, 16: 2.0}


class UBoltFamily(BaseFamily):
    name = "u_bolt"
    standard = "DIN 3570"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _DIN3570[:4]
        elif difficulty == "medium":
            pool = _DIN3570[2:6]
        else:
            pool = _DIN3570[4:]

        dn, rod_d, e, r_bend, leg_L = pool[int(rng.integers(0, len(pool)))]
        params = {
            "dn_size": dn,
            "rod_diameter": rod_d,
            "center_distance": e,
            "bend_radius": r_bend,
            "leg_length": leg_L,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            plate_L = round(e + rod_d * 3, 1)
            plate_W = round(rod_d * 2.2, 1)
            plate_T = round(max(3.0, rod_d * 0.4), 1)
            hole_d = round(rod_d + 1.5, 1)
            params.update(
                plate_length=plate_L,
                plate_width=plate_W,
                plate_thickness=plate_T,
                hole_diameter=hole_d,
            )

        if difficulty == "hard":
            # DIN 934 hex nut AF (across flats) ≈ 1.5 * rod_d; height ≈ 0.8 * rod_d
            params["hex_nut_af"] = round(rod_d * 1.5, 2)
            params["hex_nut_h"] = round(rod_d * 0.8, 2)

        return params

    def validate_params(self, params: dict) -> bool:
        rod_d = params["rod_diameter"]
        e = params["center_distance"]
        r = params["bend_radius"]
        L = params["leg_length"]
        if rod_d < 5 or L < rod_d * 2 or r < rod_d * 1.2:
            return False
        if abs(r * 2 - e) > 0.5:  # DIN 3570: e = 2r
            return False
        pt = params.get("plate_thickness", 0)
        if pt and pt < 2:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        rod_r = params["rod_diameter"] / 2
        r_bend = params["bend_radius"]
        leg_L = params["leg_length"]

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout: tips at z=0, legs going up +Z to z=leg_L, bend apex at
        # z=leg_L+r_bend. Helix threads (hard) start at z=0 naturally at tips.
        # If plate is present, legs extend DOWN through plate so they fuse.
        overlap = rod_r * 0.5
        pT_val = params.get("plate_thickness", 0) or 0
        leg_z_bot = -pT_val if pT_val else 0.0
        leg_full = leg_L + overlap - leg_z_bot

        # 1. Base leg (left cylinder) — establishes solid
        ops = [
            Op(
                "transformed",
                {
                    "offset": [-r_bend, 0.0, (leg_z_bot + leg_L + overlap) / 2],
                    "rotate": [0, 0, 0],
                },
            ),
            Op("cylinder", {"height": round(leg_full, 3), "radius": round(rod_r, 3)}),
        ]

        # 2. Right leg
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [
                                    r_bend,
                                    0.0,
                                    (leg_z_bot + leg_L + overlap) / 2,
                                ],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": round(leg_full, 3),
                                "radius": round(rod_r, 3),
                            },
                        },
                    ]
                },
            )
        )

        # 3. Half-torus bend on XY plane transformed up by leg_L. Axis Y (local)
        #    = Y-parallel line at world z=leg_L. Revolve 180° sweeps above.
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, round(leg_L, 3)],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "moveTo", "args": {"x": round(r_bend, 3), "y": 0.0}},
                        {"name": "circle", "args": {"radius": round(rod_r, 3)}},
                        {
                            "name": "revolve",
                            "args": {
                                "angleDeg": 180,
                                "axisStart": [0, 0, 0],
                                "axisEnd": [0, -1, 0],
                            },
                        },
                    ],
                },
            )
        )

        # 3. Backing plate (medium+): placed below leg tips
        pL = params.get("plate_length")
        pW = params.get("plate_width")
        pT = params.get("plate_thickness")
        hd = params.get("hole_diameter")
        if pL and pW and pT:
            plate_z = -pT / 2  # just below tips (z=0)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, plate_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": round(pL, 3),
                                    "width": round(pW, 3),
                                    "height": round(pT, 3),
                                },
                            },
                        ]
                    },
                )
            )

        # 4. Hex nut welded onto each leg tip (hard)
        af = params.get("hex_nut_af")
        nh = params.get("hex_nut_h")
        if af and nh:
            nut_cz = leg_z_bot - nh / 2 + 0.5  # slight overlap with leg tip
            r_hex = af / 2  # inscribed radius (flat-to-flat radius)
            # Hex prism via 6-point polygon revolved... use polyline + extrude.
            hex_pts = []
            for k in range(6):
                ang = math.radians(30 + k * 60)
                hex_pts.append(
                    [round(r_hex * math.cos(ang), 4), round(r_hex * math.sin(ang), 4)]
                )
            for sign in (-1, 1):
                ops.append(
                    Op(
                        "union",
                        {
                            "plane": "XY",
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [sign * r_bend, 0.0, nut_cz],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "moveTo",
                                    "args": {"x": hex_pts[0][0], "y": hex_pts[0][1]},
                                },
                                {"name": "polyline", "args": {"points": hex_pts[1:]}},
                                {"name": "close"},
                                {
                                    "name": "extrude",
                                    "args": {
                                        "distance": round(nh / 2, 4),
                                        "both": True,
                                    },
                                },
                            ],
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
