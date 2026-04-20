"""Twist drill — parametric straight-shank twist drill per DIN 338.

Follows the manual prototype in tmp/manual_family_previews/manual_twisted_drill.py:
flute sketch (outer circle R0 minus two mirror-symmetric cutter faces) twist-
extruded along Z, then tip-shaped via a cone-revolved cut tool.

Geometry driven by DIN 338 + drilling geometry constants:
  - Micro-geometry fixed: r_phi = 0.18·R0, Ra = 0.6·R0, phi_deg = 30°
  - Helix angle γ ≈ 28° via pitch P = 2π·R0 / tan(γ), range P/R0 ∈ [11, 13.5]
  - Flute length L/R0 ∈ [8, 15], must satisfy L > R0 / tan(θ/2)
  - Tip angle θ = 118° (standard N-type); 130°/140° for tougher materials

Tip shaping: cut a (ring R0..2·R0) ∪ (cylinder(R0) − cone(R0→apex)) tool from
the body, removing everything outside the conical envelope above straight_length.
Geometrically equivalent to the manual's body.intersect(envelope) but avoids
OCCT's flaky intersect for twisted solids.

Reference: DIN 338:2022-03 Short HSS drills with cylindrical shank — type N.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


def _arc_midpoint(
    center: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> tuple[float, float]:
    cx, cy = center
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    a2 = math.atan2(p2[1] - cy, p2[0] - cx)
    delta = a2 - a1
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi
    amid = a1 + 0.5 * delta
    radius = math.hypot(p1[0] - cx, p1[1] - cy)
    return (cx + radius * math.cos(amid), cy + radius * math.sin(amid))


def _build_cutter_wire_ops(R0: float, r_phi: float, Ra: float, phi_deg: float) -> list:
    """Emit Op dicts producing the single-side cutter profile closed wire.

    Math ported verbatim from the DIN 338 manual prototype: big relief
    arc (Ca, Ra) + small back arc (Cb, Rb) + outer rim arc on R0.
    """
    phi = math.radians(phi_deg)
    Ipt = (0.0, r_phi)
    R = (R0 * math.cos(phi), R0 * math.sin(phi))
    Rb = (R0**2 - 2.0 * R0 * r_phi * math.sin(phi) + r_phi**2) / (
        2.0 * (R0 * math.sin(phi) - r_phi)
    )
    Ca = (0.0, r_phi + Ra)
    Cb = (0.0, r_phi + Rb)
    y_q = (R0**2 + r_phi**2 + 2.0 * r_phi * Ra) / (2.0 * (r_phi + Ra))
    x_q = -math.sqrt(max(R0**2 - y_q**2, 0.0))
    Q = (x_q, y_q)

    mid_big = _arc_midpoint(Ca, Q, Ipt)
    mid_small = _arc_midpoint(Cb, Ipt, R)

    theta_q = math.atan2(Q[1], Q[0])
    theta_r = math.atan2(R[1], R[0])
    if theta_q < theta_r:
        theta_q += 2.0 * math.pi
    theta_mid = 0.5 * (theta_q + theta_r)
    mid_outer = (R0 * math.cos(theta_mid), R0 * math.sin(theta_mid))

    def _r(p):
        return (round(p[0], 5), round(p[1], 5))

    return [
        {"name": "moveTo", "args": {"x": round(Q[0], 5), "y": round(Q[1], 5)}},
        {
            "name": "threePointArc",
            "args": {"point1": _r(mid_big), "point2": _r(Ipt)},
        },
        {
            "name": "threePointArc",
            "args": {"point1": _r(mid_small), "point2": _r(R)},
        },
        {
            "name": "threePointArc",
            "args": {"point1": _r(mid_outer), "point2": _r(Q)},
        },
        {"name": "close", "args": {}},
    ]


class TwistedDrillFamily(BaseFamily):
    name = "twisted_drill"
    standard = "DIN 338"

    def sample_params(self, difficulty: str, rng) -> dict:
        # Manual range: L/R0 ∈ [8, 15], P/R0 ∈ [11, 13.5]. One range for all
        # difficulties — twist-extrude + boolean tip cut is inherently hard.
        rod_radius = float(
            rng.choice([1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0])
        )
        tip_angle = float(rng.choice([118.0, 130.0, 140.0]))
        pitch = round(float(rng.uniform(11.0 * rod_radius, 13.5 * rod_radius)), 2)
        tip_height = rod_radius / math.tan(math.radians(tip_angle / 2.0))
        l_min = max(8.0 * rod_radius, tip_height + 2.0)
        l_max = 15.0 * rod_radius
        rod_length = round(float(rng.uniform(l_min, l_max)), 1)

        return {
            "rod_radius": rod_radius,
            "rod_length": rod_length,
            "pitch": pitch,
            "tip_angle": tip_angle,
            "difficulty": difficulty,
            "base_plane": "XY",
        }

    def validate_params(self, params: dict) -> bool:
        R0 = params["rod_radius"]
        L = params["rod_length"]
        P = params["pitch"]
        theta = params["tip_angle"]

        if R0 < 0.5 or R0 > 12.0:
            return False
        if P <= 0 or P > 200.0:
            return False
        if theta <= 60.0 or theta >= 175.0:
            return False
        tip_height = R0 / math.tan(math.radians(theta / 2.0))
        if L <= tip_height + 2.0 or L > 300.0:
            return False
        # Manual helix-angle window
        if P < 10.0 * R0 or P > 14.0 * R0:
            return False
        if L < 7.0 * R0 or L > 16.0 * R0:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "hard")
        R0 = params["rod_radius"]
        L = params["rod_length"]
        P = params["pitch"]
        theta = params["tip_angle"]

        r_phi = round(0.18 * R0, 4)
        Ra = round(0.6 * R0, 4)
        phi_deg = 30.0

        # Manual uses a 5 mm overshoot then intersects with the envelope.
        # That boolean is flaky in this OCCT build, so we twist-extrude to the
        # exact length and cut the tip region with a ring + (cyl − cone) tool.
        total_twist = round(360.0 * (L / P), 3)
        tip_height = round(R0 / math.tan(math.radians(theta / 2.0)), 3)
        straight_length = round(L - tip_height, 3)
        hh = round(tip_height + 0.1, 3)

        wire_ops = _build_cutter_wire_ops(R0, r_phi, Ra, phi_deg)

        cone_ops = [
            {"name": "workplane_offset", "args": {"offset": straight_length}},
            {"name": "circle", "args": {"radius": round(R0, 3)}},
            {"name": "workplane_offset", "args": {"offset": tip_height}},
            {"name": "circle", "args": {"radius": 0.05}},
            {"name": "loft", "args": {"combine": True}},
        ]
        inner_notch_ops = [
            {"name": "workplane_offset", "args": {"offset": straight_length}},
            {"name": "circle", "args": {"radius": round(R0, 3)}},
            {"name": "extrude", "args": {"distance": hh}},
            {"name": "cut", "args": {"ops": cone_ops}},
        ]
        tool_ops = [
            {"name": "workplane_offset", "args": {"offset": straight_length}},
            {"name": "circle", "args": {"radius": round(R0 * 2.0, 3)}},
            {"name": "circle", "args": {"radius": round(R0, 3)}},
            {"name": "extrude", "args": {"distance": hh}},
            {"name": "union", "args": {"ops": inner_notch_ops}},
        ]

        ops = [
            Op(
                "sketch_subtract",
                {
                    # 0.99·R0: cutter arcs reach R0 so they punch cleanly through
                    # the base disk rim — avoids slivers from perfect tangency.
                    "outer_radius": round(R0 * 0.99, 4),
                    "profiles": [
                        {"wire_ops": wire_ops, "rotate_deg": 0.0},
                        {"wire_ops": wire_ops, "rotate_deg": 180.0},
                    ],
                },
            ),
            Op("placeSketch", {}),
            Op("twistExtrude", {"distance": L, "angle": total_twist}),
            Op("cut", {"ops": tool_ops}),
        ]

        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,  # flutes break rotational symmetry
        }

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
