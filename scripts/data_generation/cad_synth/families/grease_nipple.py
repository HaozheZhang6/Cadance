"""Grease nipple — DIN 71412 Type A (straight) lubrication fitting.

Single body of revolution (polyline + revolve on XZ plane, axis = world Z)
plus an external hex flange and an axial grease passage. The revolved
profile traces (per user-verified manual_grease_nipple_adj.py):

  bottom (thread entry with 45° chamfer z=0.7)
    → thread cylinder  (d1/2, 0..l)
    → neck transition  (drop in radius to d_neck = d2 - 1.0)
    → straight neck    (up through head_base_z = l + b)
    → short neck rise  (up to head_max_z - taper_height)
    → 45° taper up     (outward to d2/2 at head_max_z = h - 3.2)
    → shoulder to apex (inward to d_top/2 = 0.275·d2 at z = h)
    → axis closure     (back to center at z = h)

Catalog per DIN 71412 Type A — head geometry fixed for all thread sizes;
only thread diameter (d1) and hex AF (s) vary.

Keys: thread_code (str). Columns (all fixed except d1, s):
  d1     = thread nominal diameter
  s      = hex AF (across flats)
  h      = total height (fixed 16)
  l      = thread length below flange (fixed 5.5)
  d2     = head max outer diameter (fixed 6.5)
  b      = hex flange thickness (fixed 3.0)
  z      = bottom thread chamfer length (fixed 0.7)

Easy:   M6x1 small-hex / M6x1 std
Medium: M8x1 std / M8x1 large-hex
Hard:   M10x1 std / M10x1 large-hex

Reference: DIN 71412:1987-05 Type A.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

_DIN71412_A = {
    "M6x1_s7": {"d1": 6.0, "s": 7.0},
    "M6x1_s9": {"d1": 6.0, "s": 9.0},
    "M8x1_s9": {"d1": 8.0, "s": 9.0},
    "M8x1_s11": {"d1": 8.0, "s": 11.0},
    "M10x1_s11": {"d1": 10.0, "s": 11.0},
    "M10x1_s14": {"d1": 10.0, "s": 14.0},
}

# Fixed head geometry per DIN 71412 Type A
_H = 16.0
_L = 5.5
_D2 = 6.5
_B = 3.0
_Z_CHAMFER = 0.7
_BORE_D = 2.5


class GreaseNippleFamily(BaseFamily):
    """DIN 71412 Type A straight grease nipple (single revolve body)."""

    name = "grease_nipple"
    standard = "DIN 71412"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = ["M6x1_s7", "M6x1_s9"]
        elif difficulty == "medium":
            pool = ["M8x1_s9", "M8x1_s11", "M6x1_s9"]
        else:
            pool = ["M10x1_s11", "M10x1_s14", "M8x1_s11"]

        code = str(rng.choice(pool))
        row = _DIN71412_A[code]
        params = {
            "thread_code": code,
            "d_thread": float(row["d1"]),
            "s": float(row["s"]),
            "h": _H,
            "l": _L,
            "d2": _D2,
            "b": _B,
            "z": _Z_CHAMFER,
            "bore_d": _BORE_D,
            "difficulty": difficulty,
            "base_plane": "XZ",
        }
        return params

    def validate_params(self, params: dict) -> bool:
        d1, s = params["d_thread"], params["s"]
        if d1 <= 0:
            return False
        # hex across-corners must clear the thread diameter
        if s * 2 / math.sqrt(3) <= d1:
            return False
        if s < d1 + 0.5:
            return False
        if params["z"] >= params["l"] * 0.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1 = params["d_thread"]
        s = params["s"]
        h = params["h"]
        thread_len = params["l"]
        d2 = params["d2"]
        b = params["b"]
        z = params["z"]
        bore_d = params["bore_d"]

        d_neck = d2 - 1.0
        d_top = 0.55 * d2
        head_base_z = thread_len + b
        head_max_z = h - 3.2
        taper_height = (d2 - d_neck) / 2
        neck_straight = head_max_z - taper_height - head_base_z
        if neck_straight < 0.2:
            neck_straight = 0.2
            head_max_z = head_base_z + neck_straight + taper_height

        half_d1 = round(d1 / 2, 3)
        half_d_neck = round(d_neck / 2, 3)
        half_d2 = round(d2 / 2, 3)
        half_d_top = round(d_top / 2, 3)
        hex_across_corners = round(s * 2 / math.sqrt(3), 3)
        lr = round(thread_len, 3)
        zr = round(z, 3)
        hbr = round(head_base_z, 3)
        h_straight_top = round(head_base_z + neck_straight, 3)
        hmr = round(head_max_z, 3)
        hr = round(h, 3)
        bore_r = round(bore_d / 2, 3)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": True,
            "rotational": False,  # hex flange breaks rotational symmetry
        }

        ops: list = []

        # 1. Revolve profile on XZ plane around world Z axis.
        # Local (u, v) = (X, Z) world; revolve axis (0,0,0)→(0,1,0) local = world Z.
        ops.append(Op("moveTo", {"x": 0.0, "y": 0.0}))
        ops.append(Op("lineTo", {"x": round(half_d1 - zr, 3), "y": 0.0}))
        ops.append(Op("lineTo", {"x": half_d1, "y": zr}))
        ops.append(Op("lineTo", {"x": half_d1, "y": lr}))
        ops.append(Op("lineTo", {"x": half_d_neck, "y": lr}))
        ops.append(Op("lineTo", {"x": half_d_neck, "y": hbr}))
        ops.append(Op("lineTo", {"x": half_d_neck, "y": h_straight_top}))
        ops.append(Op("lineTo", {"x": half_d2, "y": hmr}))
        ops.append(Op("lineTo", {"x": half_d_top, "y": hr}))
        ops.append(Op("lineTo", {"x": 0.0, "y": hr}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {"angleDeg": 360, "axisStart": [0, 0, 0], "axisEnd": [0, 1, 0]},
            )
        )

        # 2. Hex flange on XY plane (z = l..l+b).
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "workplane_offset", "args": {"offset": lr}},
                        {
                            "name": "polygon",
                            "args": {"n": 6, "diameter": hex_across_corners},
                        },
                        {"name": "extrude", "args": {"distance": round(b, 3)}},
                    ],
                },
            )
        )

        # 3. Axial grease passage (through-bore) on XY plane.
        ops.append(
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "transformed", "args": {"offset": [0, 0, -1]}},
                        {"name": "circle", "args": {"radius": bore_r}},
                        {"name": "extrude", "args": {"distance": round(h + 2, 3)}},
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
            base_plane="XZ",
        )
