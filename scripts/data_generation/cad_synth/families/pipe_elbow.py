"""Pipe elbow — hollow swept tube with 90° radiusArc bend + flanged ends.

ASME B16.9 standard butt-weld fittings, NPS (nominal pipe size) series.
Pipe OD and wall thickness from ASME B36.10M Schedule 40 (most common).

Table: (NPS_label, OD_mm, wall_Sch40_mm)
  bend_radius = 1.5 × NPS (long-radius elbow, per ASME B16.9 Table 1)

Easy:   bare hollow elbow tube
Medium: + neck + plate flange on both ends
Hard:   + bolt holes on both flanges

Reference: ASME B16.9-2018 — Factory-made wrought fittings; ASME B36.10M Sch40 OD/wall table
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ASME B36.10M Schedule 40 — (NPS_label, OD_mm, wall_mm)
# bend_radius_mm = 38.1 * NPS_inch (long-radius per B16.9)
_ASME_B369_SCH40 = [
    ("NPS 1/2", 21.3, 2.77, 19.05),  # OD=21.3, wall=2.77, bend_r=19.05
    ("NPS 3/4", 26.7, 2.87, 28.58),
    ("NPS 1", 33.4, 3.38, 38.10),
    ("NPS 1-1/4", 42.2, 3.56, 47.63),
    ("NPS 1-1/2", 48.3, 3.68, 57.15),
    ("NPS 2", 60.3, 3.91, 76.20),
    ("NPS 2-1/2", 73.0, 5.16, 95.25),
    ("NPS 3", 88.9, 5.49, 114.30),
    ("NPS 4", 114.3, 6.02, 152.40),
    ("NPS 6", 168.3, 7.11, 228.60),
]
_SMALL = _ASME_B369_SCH40[:4]  # NPS 1/2–1-1/4
_MID = _ASME_B369_SCH40[:7]  # NPS 1/2–2-1/2
_ALL = _ASME_B369_SCH40


class PipeElbowFamily(BaseFamily):
    name = "pipe_elbow"
    standard = "ASME B16.9"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        nps, od_mm, wall_mm, bend_r_mm = pool[int(rng.integers(0, len(pool)))]
        outer_r = round(od_mm / 2, 2)
        wall_t = round(wall_mm, 2)
        inner_r = round(outer_r - wall_t, 2)

        # B16.9 long-radius: bend centerline = 1.5 × NPS nominal pipe size
        bend_r = round(bend_r_mm, 1)
        # B16.9 end tangent (straight section): min 25mm or 1×OD
        lead_l = round(max(25.0, od_mm), 1)
        trail_l = lead_l

        params = {
            "nps": nps,
            "outer_radius": outer_r,
            "wall_thickness": wall_t,
            "inner_radius": inner_r,
            "lead_length": lead_l,
            "bend_radius": bend_r,
            "trail_length": trail_l,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            neck_r = round(outer_r * 1.25, 1)
            neck_l = round(outer_r * 0.5, 1)
            flange_r = round(neck_r * 1.6, 1)
            flange_t = round(outer_r * 0.4, 1)
            params.update(
                neck_radius=neck_r,
                neck_length=neck_l,
                flange_radius=flange_r,
                flange_thickness=flange_t,
            )

        if difficulty == "hard":
            n_bolts = 4 if od_mm <= 60 else 6
            bolt_r = round(outer_r * 0.12, 1)
            params.update(n_bolts=n_bolts, bolt_hole_radius=bolt_r)

        return params

    def validate_params(self, params: dict) -> bool:
        or_ = params["outer_radius"]
        wt = params["wall_thickness"]
        ir = params["inner_radius"]
        br = params["bend_radius"]

        if ir < 3 or wt < 1.0:
            return False
        if br < or_ * 1.2:  # bend too tight → self-intersecting sweep
            return False

        nr = params.get("neck_radius")
        fr = params.get("flange_radius")
        if nr and nr <= or_:
            return False
        if fr and fr <= nr:
            return False

        n = params.get("n_bolts")
        bhr = params.get("bolt_hole_radius")
        if n and bhr:
            fr = params.get("flange_radius", 0)
            nr = params.get("neck_radius", 0)
            bolt_pcd = (nr + fr) / 2
            if bhr * 2 > (bolt_pcd - nr) * 0.8:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        or_ = params["outer_radius"]
        ir = params["inner_radius"]
        ll = params["lead_length"]
        br = params["bend_radius"]
        tl = params["trail_length"]

        # Outlet face position (end of trail straight, in XZ path plane)
        ox = round(br + tl, 3)  # outlet x-coordinate
        oz = round(ll + br, 3)  # outlet z-coordinate

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # -------------------------------------------------------
        # 1. Hollow tube: outer sweep − inner sweep
        # -------------------------------------------------------
        path_args = {
            "path_type": "elbow_arc",
            "lead_length": round(ll, 3),
            "bend_radius": round(br, 3),
            "trail_length": round(tl, 3),
        }
        ops.append(Op("circle", {"radius": round(or_, 3)}))
        ops.append(Op("sweep", {**path_args, "isFrenet": True}))
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {"name": "circle", "args": {"radius": round(ir, 3)}},
                        {"name": "sweep", "args": {**path_args, "isFrenet": True}},
                    ]
                },
            )
        )

        # -------------------------------------------------------
        # 2. Flanges: neck cylinder + plate disc at both ends (medium+)
        # -------------------------------------------------------
        nr = params.get("neck_radius")
        nl = params.get("neck_length")
        fr = params.get("flange_radius")
        ft = params.get("flange_thickness")

        if nr and nl and fr and ft:
            ovlp = round(or_ * 0.1, 3)  # overlap into tube for watertight boolean

            # --- Inlet (bottom, along -Z from z=0) ---
            # neck: spans z = -nl to z = ovlp (centre at -nl/2 + ovlp/2)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(-nl / 2 + ovlp / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(nl + ovlp, 3),
                                    "radius": round(nr, 3),
                                },
                            },
                        ]
                    },
                )
            )
            # plate: spans z = -(nl+ft) to z = -(nl-ovlp) — overlap with neck bottom
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(-nl - ft / 2 + ovlp / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ft, 3),
                                    "radius": round(fr, 3),
                                },
                            },
                        ]
                    },
                )
            )

            # --- Outlet (end of trail, along +X from ox, at z=oz) ---
            # neck: from ox to ox+nl along +X
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [
                                        round(ox + (nl + ovlp) / 2 - ovlp / 2, 3),
                                        0,
                                        round(oz, 3),
                                    ],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(nl + ovlp, 3),
                                    "radius": round(nr, 3),
                                },
                            },
                        ]
                    },
                )
            )
            # plate: from ox+nl to ox+nl+ft along +X
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [
                                        round(ox + nl + ft / 2, 3),
                                        0,
                                        round(oz, 3),
                                    ],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ft, 3),
                                    "radius": round(fr, 3),
                                },
                            },
                        ]
                    },
                )
            )

            # Extend bore through inlet neck+plate
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(-nl - ft - 1.0, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(nl + ft + ll + 2.0, 3),
                                    "radius": round(ir, 3),
                                },
                            },
                        ]
                    },
                )
            )
            # Extend bore through outlet neck+plate
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [round(ox - 1.0, 3), 0, round(oz, 3)],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(tl + nl + ft + 2.0, 3),
                                    "radius": round(ir, 3),
                                },
                            },
                        ]
                    },
                )
            )

            # -------------------------------------------------------
            # 3. Bolt holes (hard)
            # -------------------------------------------------------
            nb = params.get("n_bolts")
            bhr = params.get("bolt_hole_radius")
            if nb and bhr:
                bolt_pcd = round((nr + fr) / 2, 3)  # mid-annulus of flange
                for i in range(nb):
                    ang = 2 * math.pi * i / nb
                    x = round(bolt_pcd * math.cos(ang), 3)
                    y = round(bolt_pcd * math.sin(ang), 3)
                    # Inlet bolt holes (along Z)
                    ops.append(
                        Op(
                            "cut",
                            {
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [x, y, round(-nl - ft - 0.5, 3)],
                                            "rotate": [0, 0, 0],
                                        },
                                    },
                                    {
                                        "name": "cylinder",
                                        "args": {
                                            "height": round(ft + 1.0, 3),
                                            "radius": round(bhr, 3),
                                        },
                                    },
                                ]
                            },
                        )
                    )
                    # Outlet bolt holes (along X, rotated 90° around Y)
                    y2 = round(bolt_pcd * math.cos(ang), 3)
                    z2 = round(oz + bolt_pcd * math.sin(ang), 3)
                    ops.append(
                        Op(
                            "cut",
                            {
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [
                                                round(ox + nl + ft - 0.5, 3),
                                                y2,
                                                z2,
                                            ],
                                            "rotate": [0, 90, 0],
                                        },
                                    },
                                    {
                                        "name": "cylinder",
                                        "args": {
                                            "height": round(ft + 1.0, 3),
                                            "radius": round(bhr, 3),
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
