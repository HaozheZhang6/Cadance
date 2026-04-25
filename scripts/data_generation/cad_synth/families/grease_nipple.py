"""Grease nipple — DIN 71412 Type A (straight) lubrication fitting.

Single body of revolution (polyline + revolve on XZ plane, axis = world Z)
plus an external hex flange and an axial grease passage. Profile traces:

  bottom (thread entry with 45° chamfer z=0.7)
    → thread cylinder  (d1/2, 0..l)
    → neck transition  (drop in radius to d_neck/2)
    → straight neck    (up through head_base_z = l + b)
    → short neck rise  (up to h_straight_top, free)
    → taper            (outward to d_head_max/2 at head_max_z)
    → shoulder to apex (inward to d_top/2 at z = h)
    → axis closure     (back to center at z = h)

Free profile params (annotated by user, 2026-04-25):
  d_neck       ∈ (5.0, 6.0)   — was fixed 5.5
  d_head_max   ∈ (6.0, 8.0)   — was fixed 6.5 (apex stays at 0.55·6.5=3.575)
  h_straight_top ∈ (head_base_z+0.2, h - delta_taper - 0.1)
  delta_taper  ∈ (1.8, 3.0)   — head_max_z = h_straight_top + delta_taper

Catalog per DIN 71412 Type A — h, l, b, z (chamfer), bore_d fixed.
Thread diameter (d1) and hex AF (s) vary by thread_code.

Code-level mutations (geometry-preserving):
  profile_reverse  — traverse polyline CW vs CCW
  flange_edge_op   — medium/hard: chamfer or fillet on 6 vertical hex edges

Easy:   M6x1 small-hex / M6x1 std (no flange edge mod)
Medium: M8x1 std / M8x1 large-hex / M6x1 std (+ optional chamfer/fillet)
Hard:   M10x1 std / M10x1 large-hex / M8x1 large-hex (+ optional chamfer/fillet)

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

# Fixed head geometry per DIN 71412 Type A (apex shoulder narrows to 0.55·D2_NOM)
_H = 16.0
_L = 5.5
_D2_NOM = 6.5  # apex shoulder dia — line "(half_d_top, h)" stays fixed
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

        d_neck = round(float(rng.uniform(5.0, 6.0)), 3)
        d_head_max = round(float(rng.uniform(6.0, 8.0)), 3)
        delta_taper = round(float(rng.uniform(1.8, 3.0)), 3)
        head_base_z = _L + _B  # 8.5
        min_hst = head_base_z + 0.2
        max_hst = _H - delta_taper - 0.1
        h_straight_top = round(float(rng.uniform(min_hst, max_hst)), 3)

        flange_edge_op = "none"
        flange_edge_size = 0.0
        if difficulty in ("medium", "hard"):
            r = float(rng.random())
            if r < 0.4:
                flange_edge_op = "chamfer"
            elif r < 0.8:
                flange_edge_op = "fillet"
            if flange_edge_op != "none":
                flange_edge_size = round(float(rng.uniform(0.2, 0.55)), 2)

        profile_reverse = bool(rng.random() < 0.5)

        params = {
            "thread_code": code,
            "d_thread": float(row["d1"]),
            "s": float(row["s"]),
            "h": _H,
            "l": _L,
            "d2": _D2_NOM,
            "d_neck": d_neck,
            "d_head_max": d_head_max,
            "h_straight_top": h_straight_top,
            "delta_taper": delta_taper,
            "b": _B,
            "z": _Z_CHAMFER,
            "bore_d": _BORE_D,
            "flange_edge_op": flange_edge_op,
            "flange_edge_size": flange_edge_size,
            "profile_reverse": profile_reverse,
            "difficulty": difficulty,
            "base_plane": "XZ",
        }
        return params

    def validate_params(self, params: dict) -> bool:
        d1, s = params["d_thread"], params["s"]
        if d1 <= 0:
            return False
        if s * 2 / math.sqrt(3) <= d1:
            return False
        if s < d1 + 0.5:
            return False
        if params["z"] >= params["l"] * 0.5:
            return False
        d_neck = params["d_neck"]
        d_head_max = params["d_head_max"]
        # neck is the waist below the head; must be narrower than thread by ≥0.3
        if d_neck >= d1 - 0.3:
            return False
        if d_neck >= d_head_max - 0.3:
            return False
        if d_head_max <= params["d2"] - 0.5:
            return False
        head_base_z = params["l"] + params["b"]
        h_straight_top = params["h_straight_top"]
        delta_taper = params["delta_taper"]
        if h_straight_top <= head_base_z + 0.1:
            return False
        head_max_z = h_straight_top + delta_taper
        if head_max_z >= params["h"] - 0.05:
            return False
        fes = params.get("flange_edge_size", 0.0)
        if fes:
            if fes >= params["b"] * 0.5:
                return False
            if fes >= s * 0.25:
                return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d1 = params["d_thread"]
        s = params["s"]
        h = params["h"]
        thread_len = params["l"]
        d2_apex = params["d2"]
        d_neck = params["d_neck"]
        d_head_max = params["d_head_max"]
        h_straight_top = params["h_straight_top"]
        delta_taper = params["delta_taper"]
        b = params["b"]
        z = params["z"]
        bore_d = params["bore_d"]
        flange_edge_op = params.get("flange_edge_op", "none")
        flange_edge_size = float(params.get("flange_edge_size", 0.0))
        profile_reverse = bool(params.get("profile_reverse", False))

        head_base_z = thread_len + b
        head_max_z = h_straight_top + delta_taper
        d_top = 0.55 * d2_apex  # apex shoulder, fixed per user annotation

        half_d1 = round(d1 / 2, 3)
        half_d_neck = round(d_neck / 2, 3)
        half_d_head_max = round(d_head_max / 2, 3)
        half_d_top = round(d_top / 2, 3)
        hex_across_corners = round(s * 2 / math.sqrt(3), 3)
        lr = round(thread_len, 3)
        zr = round(z, 3)
        hbr = round(head_base_z, 3)
        hstr = round(h_straight_top, 3)
        hmr = round(head_max_z, 3)
        hr = round(h, 3)
        bore_r = round(bore_d / 2, 3)
        br = round(b, 3)

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": flange_edge_op == "fillet",
            "has_chamfer": True,  # bottom thread chamfer always present
            "rotational": False,
        }

        # Forward (CCW) profile vertices in (x, y) on XZ plane (local = world XZ).
        forward_pts = [
            (0.0, 0.0),
            (round(half_d1 - zr, 3), 0.0),
            (half_d1, zr),
            (half_d1, lr),
            (half_d_neck, lr),
            (half_d_neck, hbr),
            (half_d_neck, hstr),
            (half_d_head_max, hmr),
            (half_d_top, hr),
            (0.0, hr),
        ]
        pts = list(reversed(forward_pts)) if profile_reverse else forward_pts

        ops: list = []

        # 1. Revolve profile around world Z (axisEnd=(0,1,0) local on XZ).
        ops.append(Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}))
        for x, y in pts[1:]:
            ops.append(Op("lineTo", {"x": x, "y": y}))
        ops.append(Op("close", {}))
        ops.append(
            Op(
                "revolve",
                {"angleDeg": 360, "axisStart": [0, 0, 0], "axisEnd": [0, 1, 0]},
            )
        )

        # 2. Hex flange on XY (z = l..l+b).
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
                        {"name": "extrude", "args": {"distance": br}},
                    ],
                },
            )
        )

        # 2b. Optional chamfer/fillet on 6 vertical hex edges (medium/hard).
        # base_plane=XZ → "|Y" (family-code) remaps to "|Z" world, which selects
        # only the hex prism's vertical edges (revolve body has no straight verticals).
        if flange_edge_op != "none" and flange_edge_size > 0:
            ops.append(Op("edges", {"selector": "|Y"}))
            if flange_edge_op == "chamfer":
                ops.append(Op("chamfer", {"length": flange_edge_size}))
            else:
                ops.append(Op("fillet", {"radius": flange_edge_size}))

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
