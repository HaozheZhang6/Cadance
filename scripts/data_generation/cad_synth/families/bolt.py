"""Hex-head bolt — hexagonal head + cylindrical shaft + (hard) real V-threads.

ISO 4014 / ISO 4017 hex head bolts, M-series per ISO 261.
Dimensions from ISO 4014 Table 1 (partial thread) — exact standard values only.

Easy:   hex head + smooth shaft
Medium: + head top chamfer
Hard:   + real ISO metric V-thread cut at shaft tip via helix-swept triangular
        cutter (60° flank angle, pitch from ISO 261 coarse series)

Reference: ISO 4014:2011 — Table 1 (s, k, e for M3–M64); ISO 888:2012 preferred lengths;
ISO 261:1998 — coarse-pitch series for M-thread.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 4014 Table 1 — hex bolt dimensions (exact values, mm)
# (M_nominal, s_across_flats, k_head_height)
_ISO4014 = [
    (3, 5.5, 2.0),
    (4, 7.0, 2.8),
    (5, 8.0, 3.5),
    (6, 10.0, 4.0),
    (8, 13.0, 5.3),
    (10, 17.0, 6.4),
    (12, 19.0, 7.5),
    (14, 22.0, 8.8),
    (16, 24.0, 10.0),
    (18, 27.0, 11.5),
    (20, 30.0, 12.5),
    (22, 34.0, 14.0),
    (24, 36.0, 15.0),
    (27, 41.0, 17.0),
    (30, 46.0, 18.7),
    (36, 55.0, 22.5),
    (42, 65.0, 26.0),
    (48, 75.0, 30.0),
]

# ISO 261 coarse-pitch series (M_nominal → pitch_mm)
_ISO261_PITCH = {
    3: 0.5,
    4: 0.7,
    5: 0.8,
    6: 1.0,
    8: 1.25,
    10: 1.5,
    12: 1.75,
    14: 2.0,
    16: 2.0,
    18: 2.5,
    20: 2.5,
    22: 2.5,
    24: 3.0,
    27: 3.0,
    30: 3.5,
    36: 4.0,
    42: 4.5,
    48: 5.0,
}

# ISO 888 preferred length series (mm)
_ISO888_LENGTHS = [
    8,
    10,
    12,
    16,
    20,
    25,
    30,
    35,
    40,
    45,
    50,
    55,
    60,
    65,
    70,
    80,
    90,
    100,
    110,
    120,
    130,
    140,
    150,
    160,
    180,
    200,
    220,
    240,
    260,
    280,
    300,
]


class BoltFamily(BaseFamily):
    name = "bolt"
    standard = "ISO 4014"

    def sample_params(self, difficulty: str, rng) -> dict:
        # Difficulty controls M-size range
        if difficulty == "easy":
            pool = [r for r in _ISO4014 if r[0] <= 12]
        elif difficulty == "medium":
            pool = [r for r in _ISO4014 if 6 <= r[0] <= 24]
        else:
            pool = _ISO4014

        M, s, k = pool[int(rng.integers(0, len(pool)))]

        # Pick length from ISO 888 series: at least 2.5×M, at most 10×M
        valid_lens = [ln for ln in _ISO888_LENGTHS if M * 2.5 <= ln <= M * 10]
        if not valid_lens:
            valid_lens = [round(M * 4)]
        shaft_len = float(valid_lens[int(rng.integers(0, len(valid_lens)))])

        # across-corners = s / cos(30°) for hex
        head_d = round(s / math.cos(math.radians(30)), 2)

        params = {
            "nominal_size": M,
            "across_flats": float(s),
            "shaft_diameter": float(M),
            "shaft_length": shaft_len,
            "head_diameter": head_d,
            "head_height": float(k),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(k * 0.15, 1.5), 1)

        if difficulty == "hard":
            # ISO 4014 thread length per standard (approx b = 2M + 6 for M≤125mm)
            thread_l = round(min(2 * M + 6, shaft_len * 0.6), 1)
            params["thread_length"] = thread_l
            params["thread_pitch"] = float(_ISO261_PITCH[M])

        return params

    def validate_params(self, params: dict) -> bool:
        M = params["shaft_diameter"]
        hd = params["head_diameter"]
        hh = params["head_height"]
        sl = params["shaft_length"]

        if M < 3 or sl < M * 2:
            return False
        if hd < M * 1.5 or hd > M * 2.6:
            return False
        if hh < 1.5:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= hh * 0.4:
            return False

        tl = params.get("thread_length", 0)
        if tl and tl >= sl * 0.8:
            return False
        tp = params.get("thread_pitch", 0)
        if tp and tp >= M * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        M = params["shaft_diameter"]
        sl = params["shaft_length"]
        hd = params["head_diameter"]
        hh = params["head_height"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Layout: tip at z=0, shaft up, head on top.
        # This puts cq.Wire.makeHelix (built in absolute world coords starting
        # at z=0) directly at the shaft tip, where threads belong.
        # Shaft: circle + extrude upward from z=0 → spans z=[0, sl]
        ops.append(Op("circle", {"radius": round(M / 2, 4)}))
        ops.append(Op("extrude", {"distance": round(sl, 4)}))

        # Hex head on top of shaft → spans z=[sl, sl+hh]
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("polygon", {"n": 6, "diameter": hd}))
        ops.append(Op("extrude", {"distance": round(hh, 4)}))

        # Chamfer top edge of head (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Real ISO metric V-thread cut at shaft tip (hard).
        # cq.Wire.makeHelix is built in WORLD coordinates from z=0 to z=height,
        # so the layout above (tip at z=0) puts the helix directly on the
        # threaded portion. Profile pattern follows worm_screw.py: rotate the
        # workplane to the radial-axial frame, place the V apex pointing
        # radially OUTWARD so the swept solid lies INSIDE the shaft → cuts
        # V-grooves spiralling around the tip.
        tl = params.get("thread_length")
        tp = params.get("thread_pitch")
        if tl and tp:
            r_shaft = M / 2.0
            h_cut = round(tp * 0.4, 4)  # 60° V depth ≈ 0.4 × pitch
            half_w = round(h_cut * math.tan(math.radians(30.0)), 4)
            profile_pts = [
                [0.0, half_w],
                [-h_cut, 0.0],
                [0.0, -half_w],
            ]
            ops.append(
                Op(
                    "cut",
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
                                "args": {"x": round(r_shaft, 4), "y": 0.0},
                            },
                            {"name": "polyline", "args": {"points": profile_pts}},
                            {"name": "close"},
                            {
                                "name": "sweep",
                                "args": {
                                    "path_type": "helix",
                                    "path_args": {
                                        "pitch": round(tp, 4),
                                        "height": round(tl, 4),
                                        "radius": round(r_shaft, 4),
                                    },
                                    # isFrenet=False: with the small V-cutter
                                    # profile, Frenet rotates the apex into
                                    # invalid positions and fragments the
                                    # shaft (8-solid result). Fixed-frame
                                    # sweep produces one clean solid.
                                    "isFrenet": False,
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
