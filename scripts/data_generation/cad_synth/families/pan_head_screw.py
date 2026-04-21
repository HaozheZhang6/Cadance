"""Pan-head slotted screw — ISO 1580 slotted pan-head machine screw.

Cylindrical shaft + rounded "pan" head with a straight slot across the top.
Pan head has a spherical top — modeled as short cylinder blended with the
shaft by a top radius (chamfer-equivalent).

Keys: dk (head diameter), k (head height), n (slot width), t (slot depth),
d (thread / nominal), l (screw length).

Easy:   plain pan head + straight slot.
Medium: + top radius (shallow dome on head via chamfer of top edge).
Hard:   + ISO metric V-thread on shaft tip (same pattern as bolt.py).

Reference: ISO 1580:2011 — Slotted pan head screws; Tab.1 (dk, k, n, t for M1.6..M10).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 1580 Tab.1 — (d_nominal, dk_head_d, k_head_h, n_slot_w, t_slot_d)
_ISO1580 = [
    (1.6, 3.2, 1.0, 0.4, 0.35),
    (2.0, 4.0, 1.3, 0.5, 0.5),
    (2.5, 5.0, 1.5, 0.6, 0.6),
    (3.0, 5.6, 1.8, 0.8, 0.7),
    (4.0, 8.0, 2.4, 1.0, 1.0),
    (5.0, 9.5, 3.0, 1.2, 1.2),
    (6.0, 12.0, 3.6, 1.6, 1.4),
    (8.0, 16.0, 4.8, 2.0, 1.9),
    (10.0, 20.0, 6.0, 2.5, 2.4),
]

_LENGTHS = [4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 50, 60]

_ISO261_PITCH = {
    1.6: 0.35,
    2.0: 0.4,
    2.5: 0.45,
    3.0: 0.5,
    4.0: 0.7,
    5.0: 0.8,
    6.0: 1.0,
    8.0: 1.25,
    10.0: 1.5,
}


class PanHeadScrewFamily(BaseFamily):
    name = "pan_head_screw"
    standard = "ISO 1580"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = [r for r in _ISO1580 if r[0] <= 4.0]
        elif difficulty == "medium":
            pool = [r for r in _ISO1580 if 2.5 <= r[0] <= 6.0]
        else:
            pool = [r for r in _ISO1580 if r[0] >= 4.0]

        d, dk, k, n, t = pool[int(rng.integers(0, len(pool)))]
        lens = [L for L in _LENGTHS if d * 2 <= L <= d * 10]
        if not lens:
            lens = [max(8, int(d * 4))]
        L = float(rng.choice(lens))

        params = {
            "nominal_size": float(d),
            "head_d_dk": float(dk),
            "head_h_k": float(k),
            "slot_width_n": float(n),
            "slot_depth_t": float(t),
            "screw_length_l": L,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["head_edge_chamfer"] = round(k * 0.2, 2)
        if difficulty == "hard":
            params["thread_length"] = round(min(2 * d + 6, L * 0.6), 1)
            params["thread_pitch"] = float(_ISO261_PITCH[d])
        return params

    def validate_params(self, params: dict) -> bool:
        d = params["nominal_size"]
        dk = params["head_d_dk"]
        k = params["head_h_k"]
        n = params["slot_width_n"]
        t = params["slot_depth_t"]
        L = params["screw_length_l"]
        if dk <= d or k <= 0 or n >= dk * 0.5 or t >= k * 0.85:
            return False
        if L < d * 2:
            return False
        tp = params.get("thread_pitch", 0)
        if tp and tp >= d * 0.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["nominal_size"]
        dk = params["head_d_dk"]
        k = params["head_h_k"]
        n = params["slot_width_n"]
        t = params["slot_depth_t"]
        L = params["screw_length_l"]
        r_shaft = round(d / 2, 4)
        r_head = round(dk / 2, 4)

        tags = {
            "has_hole": False,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Layout: tip at z=0, shaft up, head on top (same as bolt.py)
        ops = [
            Op("circle", {"radius": r_shaft}),
            Op("extrude", {"distance": round(L, 4)}),
        ]
        # Pan head
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": r_head}))
        ops.append(Op("extrude", {"distance": round(k, 4)}))

        # Top edge chamfer to suggest pan dome (medium+)
        ch = params.get("head_edge_chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Slot across head top: box cut length=dk, width=n, depth=t
        slot_z = L + k - t / 2  # slot floor center z
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, slot_z],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "box",
                            "args": {
                                "length": round(dk + 0.4, 4),
                                "width": round(n, 4),
                                "height": round(t * 2 + 0.2, 4),
                            },
                        },
                    ]
                },
            )
        )

        # Hard: V-thread cut at shaft tip (same pattern as bolt.py)
        tl = params.get("thread_length")
        tp = params.get("thread_pitch")
        if tl and tp:
            h_cut = round(tp * 0.4, 4)
            half_w = round(h_cut * math.tan(math.radians(30.0)), 4)
            profile_pts = [[0.0, half_w], [-h_cut, 0.0], [0.0, -half_w]]
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {"offset": [0, 0, 0], "rotate": [90, 0, 0]},
                            },
                            {"name": "center", "args": {"x": r_shaft, "y": 0.0}},
                            {"name": "polyline", "args": {"points": profile_pts}},
                            {"name": "close"},
                            {
                                "name": "sweep",
                                "args": {
                                    "path_type": "helix",
                                    "path_args": {
                                        "pitch": round(tp, 4),
                                        "height": round(tl, 4),
                                        "radius": r_shaft,
                                    },
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
