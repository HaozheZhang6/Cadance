"""Wall anchor (plastic expansion plug) — Fischer SX-style.

Cylindrical body with a flange/rim on one end, a tapered tip on the other,
and longitudinal expansion slots cut along the shank. When a screw is driven
in, the split walls spread to grip the hole.

Keys: d_nom (nominal drill hole diameter), h_ef (min anchor depth),
flange_d (collar OD), slot_count (2 or 4 splits).

Easy:   plain body + flange + central pilot bore + 2 side slots.
Medium: + tapered tip + 4 longitudinal slots.
Hard:   + external ribs (anti-rotation) on outer surface.

Reference: no active geometric standard (ETAG 001 covers metal concrete
anchors, not plastic plugs; plastic-plug geometry is vendor-proprietary).
Dimensions follow the Fischer SX series catalog (5/6/8/10/12/14 mm).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# Fischer SX-style — (d_nom, length_L, flange_d, pilot_bore_d, tip_taper_len)
_WALL_ANCHORS = [
    (5.0, 25.0, 7.5, 3.0, 3.0),
    (6.0, 30.0, 9.0, 3.5, 4.0),
    (8.0, 40.0, 11.5, 4.5, 5.0),
    (10.0, 50.0, 14.0, 5.5, 6.0),
    (12.0, 60.0, 17.0, 6.5, 7.0),
    (14.0, 70.0, 19.5, 7.5, 8.0),
]


class WallAnchorFamily(BaseFamily):
    name = "wall_anchor"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _WALL_ANCHORS[:3]
        elif difficulty == "medium":
            pool = _WALL_ANCHORS[1:5]
        else:
            pool = _WALL_ANCHORS[2:]

        d_nom, L, fd, bd, tip_L = pool[int(rng.integers(0, len(pool)))]
        params = {
            "d_nom": float(d_nom),
            "length_L": float(L),
            "flange_d": float(fd),
            "pilot_bore_d": float(bd),
            "tip_taper_length": float(tip_L),
            "slot_count": 2 if difficulty == "easy" else 4,
            "slot_length": round(L * 0.55, 1),
            "slot_width": round(d_nom * 0.18, 2),
            "difficulty": difficulty,
        }
        if difficulty == "easy":
            params["tip_taper_length"] = 0.0
        if difficulty == "hard":
            params["rib_count"] = int(rng.choice([3, 4, 5, 6]))  # was always 4
            params["rib_h"] = round(d_nom * 0.18, 2)
        # slot count free in {2,3,4,6}
        params["slot_count"] = int(rng.choice([2, 3, 4, 6]))
        params["slot_length"] = round(L * 0.55, 1)
        params["slot_width"] = round(d_nom * 0.18, 2)
        # Code-syntax mutations
        params["flange_form"] = str(rng.choice(["cylinder", "extrude"]))
        return params

    def validate_params(self, params: dict) -> bool:
        d = params["d_nom"]
        L = params["length_L"]
        fd = params["flange_d"]
        bd = params["pilot_bore_d"]
        if fd <= d or bd >= d * 0.75:
            return False
        if L < d * 3:
            return False
        sl = params["slot_length"]
        if sl >= L * 0.85:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["d_nom"]
        L = params["length_L"]
        fd = params["flange_d"]
        bd = params["pilot_bore_d"]
        tip_L = params["tip_taper_length"]
        sc = params["slot_count"]
        sl = params["slot_length"]
        sw = params["slot_width"]
        flange_t = round(max(d * 0.45, 3.0), 2)

        r_body = round(d / 2, 4)
        r_flange = round(fd / 2, 4)
        r_bore = round(bd / 2, 4)

        tags = {
            "has_hole": True,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout: flange at z=[0, flange_t]; body below going -Z to z=-L.
        # Tip (if any) is a truncated cone from z=-(L-tip_L) down to z=-L.
        body_z_top = 0.0
        body_z_bot = -L + tip_L  # straight cylindrical part goes to here
        tip_z_bot = -L
        straight_len = body_z_top - body_z_bot

        flange_form = params.get("flange_form", "cylinder")
        # Flange (base solid)
        if flange_form == "cylinder":
            ops = [
                Op(
                    "transformed",
                    {"offset": [0, 0, flange_t / 2], "rotate": [0, 0, 0]},
                ),
                Op("cylinder", {"height": round(flange_t, 4), "radius": r_flange}),
            ]
        else:
            ops = [
                Op("circle", {"radius": r_flange}),
                Op("extrude", {"distance": round(flange_t, 4)}),
            ]
        # Body straight part
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, (body_z_top + body_z_bot) / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": round(straight_len, 4),
                                "radius": r_body,
                            },
                        },
                    ],
                },
            )
        )
        # Tapered tip (medium+)
        if tip_L > 0:
            # Build a tapered cylinder from r_body down to r_body*0.3 over tip_L.
            # Use revolve of a trapezoid in XZ profile.
            r_tip = round(r_body * 0.3, 4)
            # Place profile in XZ relative to world, but we're in XY top-level —
            # wrap in a union on XZ plane.
            ops.append(
                Op(
                    "union",
                    {
                        "plane": "XZ",
                        "ops": [
                            {"name": "moveTo", "args": {"x": 0.0, "y": body_z_bot}},
                            {"name": "lineTo", "args": {"x": r_body, "y": body_z_bot}},
                            {"name": "lineTo", "args": {"x": r_tip, "y": tip_z_bot}},
                            {"name": "lineTo", "args": {"x": 0.0, "y": tip_z_bot}},
                            {"name": "close", "args": {}},
                            {
                                "name": "revolve",
                                "args": {
                                    "angleDeg": 360,
                                    "axisStart": [0, 0, 0],
                                    "axisEnd": [0, 1, 0],
                                },
                            },
                        ],
                    },
                )
            )

        # External ribs (hard): radial fins. `rib_h` is the VISIBLE protrusion
        # past the body surface. The box is 2*rib_h long radially so half sits
        # inside the body (fuses) and half protrudes (visible fin).
        rib_count = params.get("rib_count", 0)
        rib_h = params.get("rib_h", 0)
        if rib_count and rib_h:
            rib_len_axial = round(straight_len * 0.65, 4)
            rib_w = round(d * 0.18, 4)
            rib_len_radial = round(rib_h * 2, 4)
            rib_cx = round(r_body, 4)
            rib_cz = round((body_z_top + body_z_bot) / 2, 4)
            for i in range(rib_count):
                ang = 2 * math.pi * i / rib_count
                px = round(rib_cx * math.cos(ang), 4)
                py = round(rib_cx * math.sin(ang), 4)
                ops.append(
                    Op(
                        "union",
                        {
                            "plane": "XY",
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [px, py, rib_cz],
                                        "rotate": [0, 0, math.degrees(ang)],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": rib_len_radial,
                                        "width": rib_w,
                                        "height": rib_len_axial,
                                    },
                                },
                            ],
                        },
                    )
                )

        # Expansion slots cut along body (longitudinal). Free count 2/3/4/6.
        slot_cz = round(body_z_top - sl / 2 - flange_t * 0.2, 4)
        slot_planes = []
        for i in range(sc):
            ang = 2 * math.pi * i / sc
            slot_planes.append((math.cos(ang), math.sin(ang)))
        box_L = round(d * 1.2, 4)
        box_W = sw
        for cx, cy in slot_planes:
            ang_deg = math.degrees(math.atan2(cy, cx))
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, slot_cz],
                                    "rotate": [0, 0, ang_deg],
                                },
                            },
                            {
                                "name": "box",
                                "args": {
                                    "length": box_L,
                                    "width": box_W,
                                    "height": round(sl, 4),
                                },
                            },
                        ],
                    },
                )
            )

        # Central pilot bore (through-hole for screw)
        ops.append(
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, (flange_t - L) / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": round(L + flange_t + 2, 4),
                                "radius": r_bore,
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
