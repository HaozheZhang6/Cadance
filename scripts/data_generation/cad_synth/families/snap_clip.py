"""Snap clip / spring bracket — C-profile thin-wall arc extrude.

Structural type: thin-wall C-profile (two concentric arcs) → extrude.
Covers: spring clips, retaining rings, panel fasteners, conduit clips.

Profile uses threePointArc for clean circular geometry (not polyline).

Easy:   C-profile thin wall extruded (clips onto rod/rail)
Medium: + snap finger slots (slotted tips) + chamfer
Hard:   + mounting flange + through holes
"""

import math

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class SnapClipFamily(BaseFamily):
    name = "snap_clip"

    def sample_params(self, difficulty: str, rng) -> dict:
        clip_r = rng.uniform(5, 25)  # radius of the clipped object
        wall_t = rng.uniform(1.0, min(4.0, clip_r * 0.25))  # wall thickness
        clip_length = rng.uniform(10, 50)  # extrude length
        opening_angle = rng.uniform(30, 80)  # gap angle in degrees (C opening)

        params = {
            "clip_radius": round(clip_r, 1),
            "wall_thickness": round(wall_t, 1),
            "clip_length": round(clip_length, 1),
            "opening_angle": round(opening_angle, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Limit slot depth to 25% of clip length so tips don't disconnect
            max_sd = round(clip_length * 0.25, 1)
            slot_depth = round(rng.uniform(max(1.0, clip_length * 0.10), max_sd), 1)
            # Keep slot width narrow: < 30% of wall thickness
            slot_w = round(rng.uniform(0.5, max(0.6, min(1.5, wall_t * 0.30))), 1)
            params["snap_slot_depth"] = slot_depth
            params["snap_slot_width"] = slot_w
            params["chamfer_length"] = round(
                rng.uniform(0.3, min(1.0, wall_t * 0.3)), 1
            )

        if difficulty == "hard":
            flange_w = round(rng.uniform(8, max(8.1, min(28, clip_r * 1.2))), 1)
            flange_t = round(rng.uniform(2.0, max(2.1, min(5.0, wall_t * 2.0))), 1)
            n_holes = int(rng.choice([2, 3]))
            # hole_d must be < spacing = flange_w/(n_holes+1) to prevent overlap
            max_hole_d = min(9.0, flange_w * 0.5, flange_w / (n_holes + 1) - 0.5)
            hole_d = round(rng.uniform(3.5, max(4.0, max_hole_d)), 1)
            params["flange_width"] = flange_w
            params["flange_thickness"] = flange_t
            params["n_flange_holes"] = n_holes
            params["flange_hole_diameter"] = hole_d

        return params

    def validate_params(self, params: dict) -> bool:
        cr = params["clip_radius"]
        wt = params["wall_thickness"]
        oa = params["opening_angle"]

        if wt >= cr * 0.4 or oa >= 180 or oa < 20:
            return False

        sw = params.get("snap_slot_width")
        if sw and sw >= wt * 0.35:
            return False

        sd = params.get("snap_slot_depth")
        cl = params.get("clip_length", params.get("clip_length", 10))
        if sd and sd >= cl * 0.28:
            return False

        fh = params.get("flange_hole_diameter")
        fw = params.get("flange_width")
        n_fh = params.get("n_flange_holes", 2)
        if fh and fw:
            if fh >= fw * 0.65:
                return False
            # center spacing must exceed diameter (no hole overlap)
            if fw / (n_fh + 1) <= fh:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        cr = params["clip_radius"]
        wt = params["wall_thickness"]
        clip_l = params["clip_length"]
        oa = params["opening_angle"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # C-profile using threePointArc (clean circular geometry, not polyline)
        # Arc spans from -half_arc to +half_arc degrees (through 0 = back of C)
        half_arc = 180.0 - oa / 2.0  # degrees on each side of opening
        half_rad = math.radians(half_arc)

        r_in = cr
        r_out = round(cr + wt, 3)

        # Key points on arcs (angle measured from +X axis)
        # start = -half_arc (bottom of C opening), end = +half_arc (top)
        # mid = 0° (back of C, farthest from opening)
        def _pt(r, ang_rad):
            return (round(r * math.cos(ang_rad), 4), round(r * math.sin(ang_rad), 4))

        s_outer = _pt(r_out, -half_rad)
        mid_outer = (round(r_out, 4), 0.0)          # back of C, outer
        e_outer = _pt(r_out, half_rad)
        s_inner = _pt(r_in, -half_rad)
        mid_inner = (round(r_in, 4), 0.0)            # back of C, inner
        e_inner = _pt(r_in, half_rad)

        # Profile: outer arc CCW (long way through back), gap, inner arc CW, close
        ops.append(Op("moveTo", {"x": s_outer[0], "y": s_outer[1]}))
        ops.append(Op("threePointArc", {"point1": list(mid_outer), "point2": list(e_outer)}))
        ops.append(Op("lineTo", {"x": e_inner[0], "y": e_inner[1]}))
        ops.append(Op("threePointArc", {"point1": list(mid_inner), "point2": list(s_inner)}))
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": clip_l}))

        # Chamfer (medium only)
        cl = params.get("chamfer_length")
        if cl and difficulty != "hard":
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Snap finger slots: cut radially at each tip, oriented tangentially
        # Use individual cut ops so each can be rotated to match tip angle.
        sw = params.get("snap_slot_width")
        sd = params.get("snap_slot_depth")
        if sw and sd:
            tags["has_slot"] = True
            r_mid = round((r_in + r_out) / 2, 4)
            for ang_rad in [half_rad, -half_rad]:
                cx = round(r_mid * math.cos(ang_rad), 4)
                cy = round(r_mid * math.sin(ang_rad), 4)
                ang_deg = round(math.degrees(ang_rad), 3)
                slot_z = round(clip_l - sd / 2.0, 4)
                ops.append(Op("cut", {"ops": [
                    {"name": "transformed", "args": {
                        # Rotate box so its X-axis (length) is radial at tip
                        "offset": [cx, cy, slot_z],
                        "rotate": [0.0, 0.0, ang_deg],
                    }},
                    {"name": "box", "args": {
                        "length": round(wt + 1.0, 4),  # radial: slightly over wall thickness
                        "width": round(sw, 4),           # tangential: narrow slit
                        "height": round(sd + 0.2, 4),   # +0.2 to ensure full cut
                        "centered": True,
                    }},
                ]}))

        # Mounting flange (hard)
        fw = params.get("flange_width")
        ft = params.get("flange_thickness")
        n_fh = params.get("n_flange_holes")
        fhd = params.get("flange_hole_diameter")
        if fw and ft:
            # Flange at the back of the C (positive X side)
            ops.append(Op("union", {"ops": [
                {"name": "transformed", "args": {
                    "offset": [
                        round(r_out + ft / 2 - 0.5, 4),
                        0.0,
                        round(clip_l / 2, 4),
                    ],
                    "rotate": [0.0, 0.0, 0.0],
                }},
                {"name": "box", "args": {
                    "length": ft,
                    "width": fw,
                    "height": round(clip_l, 4),
                    "centered": True,
                }},
            ]}))

        if n_fh and fhd and fw and ft:
            tags["has_hole"] = True
            spacing = fw / (n_fh + 1)
            fh_pts = [
                (
                    round(r_out + ft / 2 - 0.5, 4),
                    round(-fw / 2 + spacing * (i + 1), 4),
                )
                for i in range(n_fh)
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": fh_pts}))
            ops.append(Op("hole", {"diameter": fhd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
