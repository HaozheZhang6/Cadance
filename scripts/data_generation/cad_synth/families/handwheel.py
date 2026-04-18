"""Handwheel — DIN 950 spoke wheel with optional crank handle.

Rewritten from: tmp/manual_family_previews/manual_handwheel.py

Construction (matches manual exactly):
  1. Hub: annular cylinder (outer=hub_d/2, bore=bore_d/2), centered at z=0
     Manual: Workplane("YZ").workplane(offset=hub_start).circle(hub_r).circle(bore_r).extrude(hub_l)
  2. Rim: annular cylinder (outer=d1/2, inner=d1/2-rim_w), offset by dish along Z
     Manual: Workplane("YZ").workplane(offset=rim_start).circle(rim_ro).circle(rim_ri).extrude(rim_l)
  3. Spokes: trapezoidal profile in XY connecting hub faces → rim faces,
     extruded ±spoke_t/2, then rotated around X for each spoke
     Manual: polyline in XY plane, extrude(spoke_t/2, both=True), rotate around (1,0,0)
  4. Handle: base cylinder + grip cylinder on rim top face, with top chamfer
     Manual: Workplane("YZ").workplane(offset=handle_z_start).center(handle_r_pos,0)

DIN 950 table: d1, hub_d, bore_d, hub_l, rim_w, rim_l, dish, n_spokes, m, h_len

Easy:   hub + rim + spokes + bore + handle
Medium: + chamfer on rim outer edge
Hard:   + chamfer on rim outer edge + hub boss chamfer
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 950 standard table
# (d1, hub_d, bore_d_ref, hub_l, rim_w, rim_l, dish, n_spokes, m, h_len)
_DIN950 = [
    (125, 28, 12, 28, 15, 18, 18, 3, 8, 65),
    (160, 32, 14, 32, 18, 20, 20, 3, 10, 80),
    (200, 38, 18, 38, 22, 24, 24, 3, 10, 80),
    (250, 45, 22, 44, 26, 26, 30, 5, 12, 90),
    (315, 53, 26, 53, 28, 28, 33, 5, 12, 90),
]
_SMALL = _DIN950[:2]
_MID = _DIN950[1:4]
_ALL = _DIN950


class HandwheelFamily(BaseFamily):
    name = "handwheel"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        d1, hub_d, bore_ref, hub_l, rim_w, rim_l, dish, n_spokes, m, h_len = pool[
            int(rng.integers(0, len(pool)))
        ]

        bore_d = round(
            rng.uniform(bore_ref * 0.7, min(bore_ref * 1.2, hub_d * 0.65)), 1
        )

        params = {
            "outer_diameter": float(d1),
            "hub_diameter": float(hub_d),
            "bore_diameter": round(bore_d, 1),
            "hub_length": float(hub_l),
            "rim_width": float(rim_w),
            "rim_length": float(rim_l),
            "dish": float(dish),
            "n_spokes": n_spokes,
            "m_handle": m,
            "handle_length": float(h_len),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_rim"] = round(rng.uniform(1.5, rim_w * 0.12), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        d1 = params["outer_diameter"]
        hd = params["hub_diameter"]
        bore = params["bore_diameter"]
        rim_w = params["rim_width"]
        dish = params["dish"]
        hub_l = params["hub_length"]

        hub_r = hd / 2
        rim_ri = d1 / 2 - rim_w

        if bore / 2 >= hub_r * 0.75:
            return False
        if hub_r >= rim_ri * 0.7:
            return False
        if rim_ri <= hub_r + 6:
            return False
        if dish <= 0 or dish >= hub_l:
            return False

        cl = params.get("chamfer_rim", 0)
        if cl and cl >= rim_w * 0.4:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1 = params["outer_diameter"]
        hub_d = params["hub_diameter"]
        bore_d = params["bore_diameter"]
        hub_l = params["hub_length"]
        rim_w = params["rim_width"]
        rim_l = params["rim_length"]
        dish = params["dish"]
        n_spokes = params["n_spokes"]
        m_handle = params["m_handle"]
        h_len = params["handle_length"]

        outer_r = round(d1 / 2, 3)
        hub_r = round(hub_d / 2, 3)
        bore_r = round(bore_d / 2, 3)
        rim_ri = round(outer_r - rim_w, 3)

        # ── Spoke geometry ──
        # All cylinders use centered=True (CadQuery default).
        # Hub centered at z=0:  bottom = -hub_l/2, top = +hub_l/2
        # Rim centered at z=dish: bottom = dish-rim_l/2, top = dish+rim_l/2
        spoke_t = round(hub_d * 0.25, 3)
        r_in = round(hub_r - 2.0, 3)
        r_out = round(rim_ri + 2.0, 3)

        hub_start = round(-hub_l / 2, 3)  # = hub bottom face
        rim_start = round(dish - rim_l / 2, 3)  # = rim bottom face

        # Spoke trapezoid anchors: 2mm inset from each face
        p1 = (round(hub_start + 2.0, 3), r_in)  # near hub bottom
        p2 = (round(hub_start + hub_l - 2.0, 3), r_in)  # near hub top
        p3 = (round(rim_start + rim_l - 2.0, 3), r_out)  # near rim top
        p4 = (round(rim_start + 2.0, 3), r_out)  # near rim bottom

        # Handle dimensions (DIN 98)
        base_cyl_r = round(m_handle * 0.75, 3)
        grip_r = round(m_handle * 1.2, 3)
        base_cyl_l = 8.0
        grip_l = round(h_len - base_cyl_l, 3)
        grip_chamfer = round(m_handle * 0.4, 3)
        handle_r_pos = round((outer_r + rim_ri) / 2, 3)
        # Rim top face = dish + rim_l/2 (centered cylinder at z=dish)
        handle_z_start = round(dish + rim_l / 2, 3)

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # ── 1. Hub (solid cylinder centered at z=0) ──
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, 0.0, 0.0],
                                "rotate": [0.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(hub_l, 3), "radius": hub_r},
                        },
                    ]
                },
            )
        )

        # ── 2. Rim (solid cylinder centered at z=dish) ──
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, 0.0, round(dish, 3)],
                                "rotate": [0.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(rim_l, 3), "radius": outer_r},
                        },
                    ]
                },
            )
        )

        # ── 3. Cut bore through hub (centered at z=0, +2mm margin each side) ──
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, 0.0, 0.0],
                                "rotate": [0.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(hub_l + 4, 3), "radius": bore_r},
                        },
                    ]
                },
            )
        )

        # ── 4. Cut rim interior (centered at z=dish, +2mm margin each side) ──
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, 0.0, round(dish, 3)],
                                "rotate": [0.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(rim_l + 4, 3), "radius": rim_ri},
                        },
                    ]
                },
            )
        )

        # ── 5. Spokes ──
        # Manual: polyline in XY plane, extrude(spoke_t/2, both=True),
        #         then rotate around (1,0,0) for each spoke.
        # In Op system: union sub-op per spoke.
        # Workplane for spoke profile:
        #   Starting from XY, rotate 90° around local X to get (axial, radial) plane.
        #   Then polyline coords (axial_pos, radial_pos) → spoke trapezoid.
        for i in range(n_spokes):
            angle = round(i * 360.0 / n_spokes, 3)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            # Rotate to spoke's angular position
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, 0.0],
                                    "rotate": [0.0, 0.0, angle],
                                },
                            },
                            # Rotate to axial-radial plane (XY → XZ-like)
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, 0.0],
                                    "rotate": [90.0, 0.0, 0.0],
                                },
                            },
                            # Trapezoidal profile: (radial, axial) corners
                            # Manual: p1=(hub_start+2, r_in), p2=(hub_start+hub_l-2, r_in),
                            #         p3=(rim_start+rim_l-2, r_out), p4=(rim_start+2, r_out)
                            {
                                "name": "polyline",
                                "args": {
                                    "points": [
                                        [r_in, p1[0]],
                                        [r_in, p2[0]],
                                        [r_out, p3[0]],
                                        [r_out, p4[0]],
                                    ]
                                },
                            },
                            {"name": "close"},
                            # Extrude ±spoke_t/2 in tangential direction
                            {
                                "name": "extrude",
                                "args": {
                                    "distance": round(spoke_t / 2, 3),
                                    "both": True,
                                },
                            },
                        ]
                    },
                )
            )

        # ── 6. Chamfer rim outer edge (medium+) ──
        cl = params.get("chamfer_rim")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": round(cl, 3)}))

        # ── 7. Handle: base stub + grip on rim top face ──
        # Cylinders are centered=True, so offset = face_start + height/2
        base_center_z = round(handle_z_start + base_cyl_l / 2, 3)
        grip_center_z = round(handle_z_start + base_cyl_l + grip_l / 2, 3)
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [handle_r_pos, 0.0, base_center_z],
                                "rotate": [0.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": base_cyl_l, "radius": base_cyl_r},
                        },
                    ]
                },
            )
        )
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [handle_r_pos, 0.0, grip_center_z],
                                "rotate": [0.0, 0.0, 0.0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": grip_l, "radius": grip_r},
                        },
                    ]
                },
            )
        )
        # Chamfer grip top
        tags["has_chamfer"] = True
        ops.append(Op("edges", {"selector": ">Z"}))
        ops.append(Op("chamfer", {"length": grip_chamfer}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
