"""Twisted bracket — two perpendicular flat plates joined by a short helical twist.

Side-by-side layout along world +X:
  Plate 1 : flat in XY (thickness along Z), x ∈ [0, Lp], y ∈ [-h/2, h/2], z ∈ [-t/2, t/2]
  Twist   : x ∈ [Lp, Lp+Lt], loft between two YZ-plane rects; end rotated 90° about X
  Plate 2 : flat in XZ (thickness along Y), x ∈ [Lp+Lt, 2Lp+Lt], y ∈ [-t/2, t/2], z ∈ [-h/2, h/2]

Geometry driven by physical plausibility only (no ISO reference):
  - thickness > 0, sensible for a sheet-metal / mild-steel bent bracket
  - twist length ≥ 1.5 t to avoid self-intersecting loft
  - bolt-hole edge clearance ≥ 3 mm from any plate edge
  - 2-hole spacing ≥ 3·hole_dia along plate length

Easy:   stubby plates (Lp≈20-40 mm), 1 bolt hole per flange
Medium: medium plates (Lp≈30-60 mm), 2 bolt holes per flange
Hard:   long plates (Lp≈40-80 mm), 2 bolt holes per flange, longer twist

Reference: none (non-standard fabricated part).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class TwistedBracketFamily(BaseFamily):
    name = "twisted_bracket"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            Lp = float(rng.choice([20.0, 25.0, 30.0, 35.0, 40.0]))
            h = float(rng.choice([16.0, 18.0, 20.0, 24.0]))
            t = float(rng.choice([4.0, 5.0, 6.0]))
            Lt = round(float(rng.uniform(1.5 * t, 3.0 * t)), 1)
            n_holes = 1
        elif difficulty == "medium":
            Lp = float(rng.choice([30.0, 40.0, 50.0, 60.0]))
            h = float(rng.choice([14.0, 18.0, 22.0, 26.0]))
            t = float(rng.choice([3.0, 4.0, 5.0, 6.0]))
            Lt = round(float(rng.uniform(2.0 * t, 4.0 * t)), 1)
            n_holes = 2
        else:
            Lp = float(rng.choice([40.0, 50.0, 60.0, 70.0, 80.0]))
            h = float(rng.choice([12.0, 16.0, 20.0, 24.0]))
            t = float(rng.choice([3.0, 4.0, 5.0]))
            Lt = round(float(rng.uniform(3.0 * t, 5.0 * t)), 1)
            n_holes = 2

        # Hole diameter — scale with plate width, snap to common bolt clearance series
        hole_dia = round(float(rng.uniform(h * 0.25, h * 0.40)), 1)
        for bolt in [5.0, 6.5, 8.5, 10.5, 13.0]:
            if abs(hole_dia - bolt) < 1.2:
                hole_dia = bolt
                break

        return {
            "plate_length": Lp,
            "plate_width": h,
            "thickness": t,
            "twist_length": Lt,
            "hole_diameter": hole_dia,
            "n_holes_per_flange": n_holes,
            "twist_angle_deg": 90.0,
            "difficulty": difficulty,
            "base_plane": "XY",
        }

    def validate_params(self, params: dict) -> bool:
        Lp = params["plate_length"]
        h = params["plate_width"]
        t = params["thickness"]
        Lt = params["twist_length"]
        hd = params["hole_diameter"]
        n_holes = params["n_holes_per_flange"]

        if t <= 0 or t > 12:
            return False
        if Lp <= 0 or h <= 0:
            return False
        # Twist must be long enough for non-self-intersecting loft
        if Lt < 1.5 * t:
            return False
        if Lt > 80:
            return False
        # Bolt-hole edge clearance: ≥ 3 mm from any plate edge on both Y and X
        if hd <= 0 or hd >= h - 6:
            return False
        if hd >= Lp - 6:
            return False
        # 2 holes need spacing along plate length
        if n_holes == 2 and Lp < 3 * hd + 6:
            return False
        # Overall length bound
        if 2 * Lp + Lt > 300:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        Lp = params["plate_length"]
        h = params["plate_width"]
        t = params["thickness"]
        Lt = params["twist_length"]
        hd = params["hole_diameter"]
        n_holes = params["n_holes_per_flange"]

        half_t = round(t / 2, 3)
        x_twist_start = round(Lp, 3)
        x_plate2_center = round(1.5 * Lp + Lt, 3)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # 1. Plate 1 — flat in XY plane, thickness along Z
        ops = [
            Op(
                "transformed",
                {"offset": [round(Lp / 2, 3), 0, -half_t], "rotate": [0, 0, 0]},
            ),
            Op("rect", {"length": Lp, "width": h}),
            Op("extrude", {"distance": round(t, 3)}),
        ]

        # 2. Twist — loft between two YZ-plane rects, second rotated 90° about world X
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        # Start profile at x=Lp, normal +X (rotate [0,90,0])
                        # local X = world -Z, local Y = world Y
                        # rect(length=t, width=h) → Z extent=t, Y extent=h → matches plate 1 +X face
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [x_twist_start, 0, 0],
                                "rotate": [0, 90, 0],
                            },
                        },
                        {
                            "name": "rect",
                            "args": {"length": round(t, 3), "width": round(h, 3)},
                        },
                        # End profile at x=Lp+Lt, rotated 90° about world X (= local Z after first transform)
                        # Chained transform: offset [0,0,Lt] in local = +Lt along world X
                        # Additional rotate [0,0,90] about local Z = world X
                        # After chain: local X = world Y, local Y = world Z
                        # rect(length=t, width=h) → Y extent=t, Z extent=h → 90° rotated cross-section
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, round(Lt, 3)],
                                "rotate": [0, 0, 90],
                            },
                        },
                        {
                            "name": "rect",
                            "args": {"length": round(t, 3), "width": round(h, 3)},
                        },
                        {"name": "loft", "args": {"combine": True}},
                    ]
                },
            )
        )

        # 3. Plate 2 — flat in XZ plane, thickness along Y
        # Workplane offset (plate2_center_x, -t/2, 0), rotate -90° about X → normal +Y
        # local X = world X, local Y = world -Z; rect(Lp, h) → X extent=Lp, Z extent=h
        # extrude(t) along +Y → y ∈ [-t/2, t/2]
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [x_plate2_center, -half_t, 0],
                                "rotate": [-90, 0, 0],
                            },
                        },
                        {
                            "name": "rect",
                            "args": {"length": round(Lp, 3), "width": round(h, 3)},
                        },
                        {"name": "extrude", "args": {"distance": round(t, 3)}},
                    ]
                },
            )
        )

        # 4. Bolt holes through each plate
        hole_eps = 0.2
        hole_len = round(t + 2 * hole_eps, 3)
        r_hole = round(hd / 2, 3)

        if n_holes == 1:
            plate1_x_positions = [round(Lp / 2, 3)]
            plate2_x_positions = [x_plate2_center]
        else:
            dx = round(Lp / 4, 3)
            plate1_x_positions = [round(Lp / 2 - dx, 3), round(Lp / 2 + dx, 3)]
            plate2_x_positions = [
                round(x_plate2_center - dx, 3),
                round(x_plate2_center + dx, 3),
            ]

        # Plate 1 holes: through Z axis
        for xh in plate1_x_positions:
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [xh, 0, round(-half_t - hole_eps, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {"name": "circle", "args": {"radius": r_hole}},
                            {"name": "extrude", "args": {"distance": hole_len}},
                        ]
                    },
                )
            )

        # Plate 2 holes: through Y axis (workplane normal +Y via rotate [-90, 0, 0])
        for xh in plate2_x_positions:
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [xh, round(-half_t - hole_eps, 3), 0],
                                    "rotate": [-90, 0, 0],
                                },
                            },
                            {"name": "circle", "args": {"radius": r_hole}},
                            {"name": "extrude", "args": {"distance": hole_len}},
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
