"""Venturi tube — classical Venturi per ISO 5167-4.

Closed cross-section (inner + outer profile) revolved 360° around the tube
axis.  Straight inlet → convergent cone → throat → divergent cone → straight
outlet, with a uniform wall thickness carried through every section.

ISO 5167-4:2022 geometric constraints (§5):
  - Pipe diameter D ∈ [50, 1200] mm
  - Beta ratio β = d/D ∈ [0.3, 0.75]
  - Inlet cylinder length ≥ D
  - Convergent half-angle = 21° ± 1° (sampled in [20, 22])
  - Throat length = d (exactly)
  - Divergent half-angle ∈ [7°, 15°] (7° typical for minimum pressure loss)

Easy:   D 50–200, β 0.50–0.65, nominal 21° conv / 7° div
Medium: D 50–500, β 0.40–0.75, conv 20.5–21.5, div 7–10°
Hard:   D 50–1200, β 0.30–0.75, conv 20–22, div 10–15°, longer outlets

Reference: ISO 5167-4:2022 — Measurement of fluid flow by means of pressure
  differential devices inserted in circular cross-section conduits running
  full — Part 4: Venturi tubes.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class VenturiTubeFamily(BaseFamily):
    name = "venturi_tube"
    standard = "ISO 5167-4"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            D = float(rng.choice([50.0, 80.0, 100.0, 150.0, 200.0]))
            beta = float(rng.uniform(0.50, 0.65))
            conv_angle = 21.0
            div_angle = 7.0
        elif difficulty == "medium":
            D = float(rng.choice([80.0, 100.0, 150.0, 200.0, 300.0, 500.0]))
            beta = float(rng.uniform(0.40, 0.75))
            conv_angle = round(float(rng.uniform(20.5, 21.5)), 2)
            div_angle = float(rng.choice([7.0, 8.0, 10.0]))
        else:
            D = float(rng.choice([100.0, 200.0, 300.0, 500.0, 800.0, 1200.0]))
            beta = float(rng.uniform(0.30, 0.75))
            conv_angle = round(float(rng.uniform(20.0, 22.0)), 2)
            div_angle = float(rng.choice([10.0, 12.0, 15.0]))
        d = round(D * beta, 1)

        inlet_len = round(D * rng.uniform(1.0, 1.5), 1)
        outlet_len_mult = (
            rng.uniform(0.6, 1.0) if difficulty != "hard" else rng.uniform(1.0, 1.4)
        )
        outlet_len = round(D * outlet_len_mult, 1)
        thickness = round(D * rng.uniform(0.06, 0.12), 1)

        # Code-level mutations: polyline op vs explicit moveTo+lineTo's,
        # and forward vs reversed point order (closed wire equivalent).
        polyline_form = str(rng.choice(["polyline", "lineto"]))
        profile_reverse = bool(rng.random() < 0.5)

        return {
            "pipe_diameter": D,
            "throat_diameter": d,
            "thickness": thickness,
            "inlet_len": inlet_len,
            "outlet_len": outlet_len,
            "conv_angle_deg": conv_angle,
            "div_angle_deg": div_angle,
            "polyline_form": polyline_form,
            "profile_reverse": profile_reverse,
            "difficulty": difficulty,
            "base_plane": "XY",
        }

    def validate_params(self, params: dict) -> bool:
        D = params["pipe_diameter"]
        d = params["throat_diameter"]
        t = params["thickness"]
        il = params["inlet_len"]
        ol = params["outlet_len"]
        ca = params["conv_angle_deg"]
        da = params["div_angle_deg"]
        if not (50.0 <= D <= 1200.0):  # ISO 5167-4 §5.1.2
            return False
        if not (0.3 <= d / D <= 0.75):  # ISO 5167-4 §5.4
            return False
        if not (20.0 <= ca <= 22.0):  # ISO 5167-4 §5.2 (21°±1°)
            return False
        if not (7.0 <= da <= 15.0):  # ISO 5167-4 §5.3
            return False
        if il < D * 0.9:
            return False
        if t < 1.0 or t > D * 0.25:
            return False
        if ol < D * 0.3:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        D = params["pipe_diameter"]
        d = params["throat_diameter"]
        t = params["thickness"]
        il = params["inlet_len"]
        ol = params["outlet_len"]
        a_conv = math.radians(params["conv_angle_deg"])
        a_div = math.radians(params["div_angle_deg"])
        throat_len = d

        y0 = 0.0
        y1 = y0 + il
        y2 = y1 + ((D - d) / 2.0) / math.tan(a_conv)
        y3 = y2 + throat_len
        y4 = y3 + ((D - d) / 2.0) / math.tan(a_div)
        y5 = y4 + ol

        R, r = D / 2.0, d / 2.0
        Ro, ro = R + t, r + t

        inner = [
            (R, y0),
            (R, y1),
            (r, y2),
            (r, y3),
            (R, y4),
            (R, y5),
        ]
        outer = [
            (Ro, y5),
            (Ro, y4),
            (ro, y3),
            (ro, y2),
            (Ro, y1),
            (Ro, y0),
        ]
        section_pts = [(round(x, 4), round(y, 4)) for x, y in inner + outer]
        if params.get("profile_reverse", False):
            section_pts = list(reversed(section_pts))

        polyline_form = params.get("polyline_form", "polyline")
        if polyline_form == "polyline":
            ops = [Op("polyline", {"points": section_pts})]
        else:
            # Explicit moveTo + lineTo chain — same closed wire, different op count.
            ops = [Op("moveTo", {"x": section_pts[0][0], "y": section_pts[0][1]})]
            for x, y in section_pts[1:]:
                ops.append(Op("lineTo", {"x": x, "y": y}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {"angleDeg": 360, "axisStart": [0, 0, 0], "axisEnd": [0, 1, 0]},
            )
        )

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
