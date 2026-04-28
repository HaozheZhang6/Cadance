"""simple_symbol_pack — semantic / composite arc-based shapes.

Recognizable 2D-extrude symbols built from polyline + threePointArc:
letters, smiley, heart, arrow, etc.  Many include cut features
(workplane >Z + sketch + cutThruAll/cutBlind) for hollow / detail shapes.

All families: closed sketch in XY → extrude → optional cut features.
None are basic primitives — each must be visually identifiable as the
named symbol.

Op vocabulary (verified against pipeline/builder.py):
  - Op("circle", {"radius"})                       sketch circle
  - Op("rect", {"length","width"})                 sketch rect
  - Op("moveTo", {"x","y"})                        pen-down
  - Op("lineTo", {"x","y"})                        sketch line
  - Op("threePointArc", {"point1","point2"})       through-pt, end-pt
  - Op("close", {})                                close wire
  - Op("extrude", {"distance"})                    extrude profile
  - Op("workplane", {"selector": ">Z"})            top face for cuts
  - Op("center", {"x","y"})                        offset on workplane
  - Op("cutThruAll", {})                           through cut
  - Op("cutBlind", {"depth"})                      blind cut

Family list:
  simple_letter_s_plate          extruded letter S
  simple_letter_c_plate          extruded letter C
  simple_letter_g_plate          extruded letter G
  simple_smiley_plate            disc + 2 eye holes + arc-mouth slot cut
  simple_hollow_key_plate        keystem + central oval cutout
  simple_curved_arrow_plate      half-ring arc with arrow head
  simple_heart_plate             two arc lobes + V bottom
  simple_plate_with_s_cut        rectangular plate with S-shaped slot cut
  simple_question_mark_plate     top arc + drop + bottom dot
  simple_yin_yang_plate          disc + S-curve groove + 2 small holes
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- shared helpers --------------------------------------------------


def _r3(x):
    return round(float(x), 3)


def _round_pt(p):
    return (_r3(p[0]), _r3(p[1]))


def _arc_through(cx, cy, r, a0, a1):
    """Mid-arc point at angle (a0+a1)/2 around (cx,cy) radius r."""
    am = 0.5 * (a0 + a1)
    return (cx + r * math.cos(am), cy + r * math.sin(am))


def _arc_pt(cx, cy, r, a):
    return (cx + r * math.cos(a), cy + r * math.sin(a))


# ---------- families --------------------------------------------------------


# 1. simple_letter_s_plate — extruded letter "S"
class SimpleLetterSPlateFamily(BaseFamily):
    name = "simple_letter_s_plate"
    standard = "N/A"
    REF = "imagined: extruded letter 'S' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(20, 40)), 1)
        # stroke width as fraction of scale
        stroke = round(scale * float(rng.uniform(0.22, 0.32)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "scale": scale,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 18
            and p["stroke"] >= 4
            and p["stroke"] < p["scale"] * 0.45
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # S = top semicircle (top lobe) + bottom semicircle (bottom lobe), opposite
        # curvature. Build as outer outline (CCW) of S-shape with stroke width w.
        # Place top-lobe center at (0, +R), bottom-lobe center at (0, -R) where R=scale/2.
        # Outer radius = R + w/2, inner = R - w/2.
        R = p["scale"] / 2.0
        w = p["stroke"]
        # Build S as a sinusoidal spine of amplitude R/2, sampled densely,
        # then offset by ±w/2 perpendicular to the tangent to form a closed
        # polyline outline.
        # Spine parametric:
        #   x(t) = (R/2) * sin(2π t),  y(t) = R - 2R t,  t ∈ [0, 1]
        # At t=0:   (0,  R)   — top center of S
        # At t=0.25:( R/2,  R/2 ) — top-right crest
        # At t=0.5: (0, 0)    — middle (zero-crossing)
        # At t=0.75:(-R/2, -R/2) — bottom-left trough
        # At t=1:   (0, -R)   — bottom center of S
        # Visually reads as a Z-symmetric S with both tips flaring in +x.
        rA = R / 2.0
        spine_pts: list[tuple[float, float]] = []
        n_spine = 60
        amp = rA
        for i in range(n_spine + 1):
            t = i / n_spine
            xs = amp * math.sin(2.0 * math.pi * t)
            ys = R - 2.0 * R * t
            spine_pts.append((xs, ys))

        # Offset spine ±w/2 perpendicular to tangent.
        def offset_curve(pts, off):
            out = []
            for k in range(len(pts)):
                if k == 0:
                    dx = pts[1][0] - pts[0][0]
                    dy = pts[1][1] - pts[0][1]
                elif k == len(pts) - 1:
                    dx = pts[-1][0] - pts[-2][0]
                    dy = pts[-1][1] - pts[-2][1]
                else:
                    dx = pts[k + 1][0] - pts[k - 1][0]
                    dy = pts[k + 1][1] - pts[k - 1][1]
                m = math.hypot(dx, dy)
                if m < 1e-9:
                    m = 1e-9
                # Perpendicular: rotate +90° → (-dy, dx) normalized
                nx = -dy / m
                ny = dx / m
                out.append((pts[k][0] + off * nx, pts[k][1] + off * ny))
            return out

        outer = offset_curve(spine_pts, +w / 2.0)
        inner = offset_curve(spine_pts, -w / 2.0)
        # Build outline: outer (start → end) + inner (end → start, reversed) +
        # close.
        outline = outer + list(reversed(inner))
        outline = [_round_pt(p_) for p_ in outline]
        ops = [
            Op("polyline", {"points": outline}),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "letter": "S",
                "ref": self.REF,
            },
        )


# 2. simple_letter_c_plate — extruded letter "C" (3/4 arc with thickness)
class SimpleLetterCPlateFamily(BaseFamily):
    name = "simple_letter_c_plate"
    standard = "N/A"
    REF = "imagined: extruded letter 'C' nameplate / clip-shape blank"

    def sample_params(self, difficulty, rng):
        r_outer = round(float(rng.uniform(20, 40)), 1)
        stroke = round(r_outer * float(rng.uniform(0.22, 0.35)), 1)
        # opening angle: how much of the C is open (gap on the right)
        gap_deg = float(rng.choice([60.0, 80.0, 100.0, 120.0]))
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "r_outer": r_outer,
            "stroke": stroke,
            "gap_deg": gap_deg,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_outer"] >= 12
            and p["stroke"] >= 4
            and p["stroke"] < p["r_outer"] * 0.5
            and 30 <= p["gap_deg"] <= 180
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # C shape: annular sector. Gap centered on +x axis.
        # Outer arc sweeps from angle a0=+gap/2 CCW to a1=2π-gap/2.
        # Inner arc sweeps back (CW from a1 to a0).
        ro = p["r_outer"]
        ri = ro - p["stroke"]
        gap = math.radians(p["gap_deg"])
        a0 = +gap / 2.0  # outer arc start (lower-right of opening)
        a1 = 2.0 * math.pi - gap / 2.0  # outer arc end (upper-right of opening)
        # Outer arc through angle π (the back-left of the C)
        outer_through = _arc_pt(0, 0, ro, math.pi)
        outer_end = _arc_pt(0, 0, ro, a1)
        inner_through = _arc_pt(0, 0, ri, math.pi)
        inner_start = _arc_pt(0, 0, ri, a0)
        outer_start = _arc_pt(0, 0, ro, a0)
        ops = [
            Op("moveTo", {"x": _r3(outer_start[0]), "y": _r3(outer_start[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(outer_through),
                    "point2": _round_pt(outer_end),
                },
            ),
            Op(
                "lineTo",
                {
                    "x": _r3(_arc_pt(0, 0, ri, a1)[0]),
                    "y": _r3(_arc_pt(0, 0, ri, a1)[1]),
                },
            ),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(inner_through),
                    "point2": _round_pt(inner_start),
                },
            ),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "letter": "C",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 3. simple_letter_g_plate — extruded letter "G"
class SimpleLetterGPlateFamily(BaseFamily):
    name = "simple_letter_g_plate"
    standard = "N/A"
    REF = "imagined: extruded letter 'G' (C-shape with horizontal serif)"

    def sample_params(self, difficulty, rng):
        r_outer = round(float(rng.uniform(20, 40)), 1)
        stroke = round(r_outer * float(rng.uniform(0.22, 0.32)), 1)
        gap_deg = float(rng.choice([70.0, 90.0, 110.0]))
        # serif length: extends inward from the lower-right tip of the C
        serif_len = round(r_outer * float(rng.uniform(0.35, 0.55)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "r_outer": r_outer,
            "stroke": stroke,
            "gap_deg": gap_deg,
            "serif_len": serif_len,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_outer"] >= 14
            and p["stroke"] >= 4
            and p["stroke"] < p["r_outer"] * 0.5
            and 40 <= p["gap_deg"] <= 160
            and p["serif_len"] >= 4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # G = C with a horizontal serif extending leftward from the upper end
        # of the C's gap. We start with the same outer/inner C arcs, but at the
        # gap-end region (a1 = upper-right), instead of going straight inward
        # to the inner radius, we go inward + then horizontal-leftward to make
        # the serif, then back up.
        ro = p["r_outer"]
        ri = ro - p["stroke"]
        gap = math.radians(p["gap_deg"])
        a0 = +gap / 2.0
        a1 = 2.0 * math.pi - gap / 2.0
        s_len = p["serif_len"]
        s_w = p["stroke"]  # serif thickness same as main stroke

        outer_start = _arc_pt(0, 0, ro, a0)
        outer_through = _arc_pt(0, 0, ro, math.pi)
        outer_end = _arc_pt(0, 0, ro, a1)
        inner_end = _arc_pt(0, 0, ri, a1)
        inner_through = _arc_pt(0, 0, ri, math.pi)
        inner_start = _arc_pt(0, 0, ri, a0)

        # Serif: from inner_end go inward (toward -x, to the left) by s_len,
        # forming a horizontal bar at the upper-right of the inner ring.
        # Bar starts at inner_end (upper-right inner point) and goes to
        # (inner_end.x - s_len, inner_end.y), then drops by s_w to make the
        # bottom of serif, then back to inner ring.
        serif_top_left = (inner_end[0] - s_len, inner_end[1])
        serif_bot_left = (inner_end[0] - s_len, inner_end[1] - s_w)
        serif_bot_right = (inner_end[0], inner_end[1] - s_w)

        ops = [
            Op("moveTo", {"x": _r3(outer_start[0]), "y": _r3(outer_start[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(outer_through),
                    "point2": _round_pt(outer_end),
                },
            ),
            Op("lineTo", {"x": _r3(inner_end[0]), "y": _r3(inner_end[1])}),
            # Serif: out to top-left of serif bar, down, back to inner ring
            Op("lineTo", {"x": _r3(serif_top_left[0]), "y": _r3(serif_top_left[1])}),
            Op("lineTo", {"x": _r3(serif_bot_left[0]), "y": _r3(serif_bot_left[1])}),
            Op("lineTo", {"x": _r3(serif_bot_right[0]), "y": _r3(serif_bot_right[1])}),
            # Now follow the inner arc from a slightly-below-a1 back to a0
            # We approximate by going from serif_bot_right (which is at angle
            # near a1 but at radius slightly > ri) and connecting via a small
            # straight to a point ON the inner arc, then arc back to a0.
            # Compute angle of serif_bot_right from origin:
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(inner_through),
                    "point2": _round_pt(inner_start),
                },
            ),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "letter": "G",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 4. simple_smiley_plate — disc + 2 eye holes + arc-mouth slot cut
class SimpleSmileyPlateFamily(BaseFamily):
    name = "simple_smiley_plate"
    standard = "N/A"
    REF = "imagined: smiley emoji medallion / button"

    def sample_params(self, difficulty, rng):
        r_face = round(float(rng.uniform(25, 45)), 1)
        thickness = round(float(rng.uniform(4, 12)), 1)
        eye_r = round(r_face * float(rng.uniform(0.08, 0.13)), 1)
        eye_off_x = round(r_face * 0.35, 1)
        eye_off_y = round(r_face * 0.30, 1)
        mouth_r = round(r_face * float(rng.uniform(0.45, 0.60)), 1)
        mouth_w = round(eye_r * 1.1, 1)  # thickness of mouth slot
        mouth_y_off = round(-r_face * 0.10, 1)
        return {
            "r_face": r_face,
            "thickness": thickness,
            "eye_r": eye_r,
            "eye_off_x": eye_off_x,
            "eye_off_y": eye_off_y,
            "mouth_r": mouth_r,
            "mouth_w": mouth_w,
            "mouth_y_off": mouth_y_off,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_face"] >= 18
            and p["eye_r"] >= 2
            and p["eye_r"] < p["r_face"] * 0.2
            and p["mouth_r"] >= 6
            and p["mouth_r"] < p["r_face"] * 0.75
            and p["thickness"] >= 2
        )

    def make_program(self, p):
        rf = p["r_face"]
        T = p["thickness"]
        er = p["eye_r"]
        ex = p["eye_off_x"]
        ey = p["eye_off_y"]
        mr = p["mouth_r"]
        mw = p["mouth_w"]
        my = p["mouth_y_off"]

        ops = [
            # Face disc
            Op("circle", {"radius": rf}),
            Op("extrude", {"distance": T}),
            # Top face for cuts
            Op("workplane", {"selector": ">Z"}),
            Op("pushPoints", {"points": [(-ex, ey), (ex, ey)]}),
            Op("hole", {"diameter": 2 * er}),
            # Mouth: arc-shaped slot cut. We build a closed arc-bar (annular
            # sector) profile centered horizontally at (0, my), opening upward
            # (smile), then cutThruAll.
            Op("workplane", {"selector": ">Z"}),
        ]
        # Mouth profile: annular sector centered at (0, my), facing DOWN
        # (sweep symmetric around -y axis). Outer r = mr + mw/2, inner = mr - mw/2,
        # sweep half-angle = π/3 (60° each side, total 120°).
        ro = mr + mw / 2.0
        ri = mr - mw / 2.0
        sweep_half = math.radians(55)  # half-sweep
        # Center of arc set at (0, my); arc opens DOWNWARD so the smile curves up.
        # Compute points relative to (0, my).
        a0 = -math.pi / 2 - sweep_half  # left tip angle (lower-left)
        a1 = -math.pi / 2 + sweep_half  # right tip angle (lower-right)
        # Wait — for a SMILE (curving up at the corners), we want the mouth
        # arc to open UP. The outer arc passes through the LOWEST point.
        # Arc-bar around angle -π/2 (down): outer points trace below center.
        # Let's instead center the arc-bar around angle +π/2... No. A smile
        # arc looks like a frown if we pick the wrong side.
        # Smile: corners up, middle down. So the lowest point of the mouth
        # is at center-bottom, corners are at upper-left and upper-right.
        # Outer arc (the bottom of the slot) passes through the lowest point.
        # If center is at (0, my+offset_up), outer arc through (-π/2 from center)
        # is the lowest. Corners at angles around (−π/2 ± 60°).
        cx = 0.0
        cy = my  # mouth arc center
        a0 = -math.pi / 2 - sweep_half
        a1 = -math.pi / 2 + sweep_half
        am = -math.pi / 2
        outer_start = _arc_pt(cx, cy, ro, a0)
        outer_mid = _arc_pt(cx, cy, ro, am)
        outer_end = _arc_pt(cx, cy, ro, a1)
        inner_end = _arc_pt(cx, cy, ri, a1)
        inner_mid = _arc_pt(cx, cy, ri, am)
        inner_start = _arc_pt(cx, cy, ri, a0)
        ops += [
            Op("moveTo", {"x": _r3(outer_start[0]), "y": _r3(outer_start[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(outer_mid),
                    "point2": _round_pt(outer_end),
                },
            ),
            Op("lineTo", {"x": _r3(inner_end[0]), "y": _r3(inner_end[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(inner_mid),
                    "point2": _round_pt(inner_start),
                },
            ),
            Op("close", {}),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "smiley": True,
                "sketch_arc": True,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 5. simple_hollow_key_plate — keystem profile + central oval cutout
class SimpleHollowKeyPlateFamily(BaseFamily):
    name = "simple_hollow_key_plate"
    standard = "N/A"
    REF = "imagined: hollow flat key blank with central oval cutout"

    def sample_params(self, difficulty, rng):
        head_r = round(float(rng.uniform(15, 25)), 1)
        shaft_w = round(head_r * float(rng.uniform(0.4, 0.7)), 1)
        shaft_len = round(head_r * float(rng.uniform(2.0, 3.5)), 1)
        thickness = round(float(rng.uniform(3, 8)), 1)
        cut_oval_l = round(head_r * float(rng.uniform(0.6, 1.0)), 1)
        cut_oval_w = round(head_r * float(rng.uniform(0.25, 0.45)), 1)
        return {
            "head_r": head_r,
            "shaft_w": shaft_w,
            "shaft_len": shaft_len,
            "thickness": thickness,
            "cut_oval_l": cut_oval_l,
            "cut_oval_w": cut_oval_w,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["head_r"] >= 8
            and p["shaft_w"] >= 5
            and p["shaft_w"] < 2 * p["head_r"] - 2
            and p["shaft_len"] >= 12
            and p["thickness"] >= 1.5
            and p["cut_oval_l"] >= 4
            and p["cut_oval_w"] >= 3
            and p["cut_oval_l"] < 2 * p["head_r"] - 4
            and p["cut_oval_w"] < p["shaft_w"] - 2
        )

    def make_program(self, p):
        # Outline: round head on +x side (semicircle of radius head_r), shaft
        # extends to -x.
        r = p["head_r"]
        hw = p["shaft_w"] / 2.0
        L = p["shaft_len"]
        # head semicircle from (0, hw) to (0, -hw) through (r, 0)
        through_x = math.sqrt(max(0.001, r * r - hw * hw))
        ops = [
            # Outer profile (key silhouette)
            Op("moveTo", {"x": _r3(0), "y": _r3(hw)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((through_x, 0)),
                    "point2": _round_pt((0, -hw)),
                },
            ),
            Op("lineTo", {"x": _r3(-L), "y": _r3(-hw)}),
            Op("lineTo", {"x": _r3(-L), "y": _r3(hw)}),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
            # Cut a central oval through the head region using slot2D
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": _r3(through_x * 0.4), "y": _r3(0)}),
            Op(
                "slot2D",
                {
                    "length": p["cut_oval_l"],
                    "width": p["cut_oval_w"],
                    "angle": 0,
                },
            ),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "hollow": True,
                "thin_plate": True,
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 6. simple_curved_arrow_plate — half-ring arc with arrow head at one end
class SimpleCurvedArrowPlateFamily(BaseFamily):
    name = "simple_curved_arrow_plate"
    standard = "N/A"
    REF = "imagined: curved arrow indicator / refresh icon shape"

    def sample_params(self, difficulty, rng):
        r_mean = round(float(rng.uniform(25, 45)), 1)
        bar_t = round(r_mean * float(rng.uniform(0.13, 0.22)), 1)
        sweep_deg = float(rng.choice([180.0, 200.0, 220.0, 240.0]))
        head_w = round(bar_t * float(rng.uniform(2.2, 3.2)), 1)
        head_len = round(bar_t * float(rng.uniform(2.0, 3.0)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "r_mean": r_mean,
            "bar_t": bar_t,
            "sweep_deg": sweep_deg,
            "head_w": head_w,
            "head_len": head_len,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_mean"] >= 15
            and p["bar_t"] >= 3
            and p["r_mean"] > p["bar_t"] + 4
            and 90 <= p["sweep_deg"] <= 300
            and p["head_w"] > p["bar_t"] + 2
            and p["head_len"] >= 4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Curved bar (arc) + triangular head at one end (a1).
        r_mean = p["r_mean"]
        bar_t = p["bar_t"]
        sweep = math.radians(p["sweep_deg"])
        ro = r_mean + bar_t / 2.0
        ri = r_mean - bar_t / 2.0
        # Sweep symmetric around +x axis
        a0 = -sweep / 2.0
        a1 = +sweep / 2.0
        am = 0.0
        outer_start = _arc_pt(0, 0, ro, a0)
        outer_mid = _arc_pt(0, 0, ro, am)
        outer_end = _arc_pt(0, 0, ro, a1)
        inner_end = _arc_pt(0, 0, ri, a1)
        inner_mid = _arc_pt(0, 0, ri, am)
        inner_start = _arc_pt(0, 0, ri, a0)
        # Arrow head at a1 (the ENDING tip of the bar):
        # tangent at a1 (CCW direction) = (-sin(a1), cos(a1))
        # outward radial = (cos(a1), sin(a1))
        # head extends in +tangent direction from the bar's end face by head_len,
        # with head_w/2 spread on each side of the bar (in radial direction).
        tan_x = -math.sin(a1)
        tan_y = math.cos(a1)
        rad_x = math.cos(a1)
        rad_y = math.sin(a1)
        # bar end face midpoint at radius r_mean, angle a1
        end_mid = _arc_pt(0, 0, r_mean, a1)
        # head outer corner (further from center)
        head_outer = (
            end_mid[0] + (p["head_w"] / 2) * rad_x,
            end_mid[1] + (p["head_w"] / 2) * rad_y,
        )
        # head inner corner (closer to center)
        head_inner = (
            end_mid[0] - (p["head_w"] / 2) * rad_x,
            end_mid[1] - (p["head_w"] / 2) * rad_y,
        )
        # head tip
        head_tip = (
            end_mid[0] + p["head_len"] * tan_x,
            end_mid[1] + p["head_len"] * tan_y,
        )
        # Outline (CCW):
        #   outer_start → arc → outer_end (bar outer edge)
        #   → head_outer (radial step out at the tip)
        #   → head_tip
        #   → head_inner (back to inner side of tip)
        #   → inner_end (radial step back to inner edge of bar)
        #   → arc → inner_start
        #   → close
        ops = [
            Op("moveTo", {"x": _r3(outer_start[0]), "y": _r3(outer_start[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(outer_mid),
                    "point2": _round_pt(outer_end),
                },
            ),
            Op("lineTo", {"x": _r3(head_outer[0]), "y": _r3(head_outer[1])}),
            Op("lineTo", {"x": _r3(head_tip[0]), "y": _r3(head_tip[1])}),
            Op("lineTo", {"x": _r3(head_inner[0]), "y": _r3(head_inner[1])}),
            Op("lineTo", {"x": _r3(inner_end[0]), "y": _r3(inner_end[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(inner_mid),
                    "point2": _round_pt(inner_start),
                },
            ),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "arrow": True,
                "ref": self.REF,
            },
        )


# 7. simple_heart_plate — two arc lobes + V bottom
class SimpleHeartPlateFamily(BaseFamily):
    name = "simple_heart_plate"
    standard = "N/A"
    REF = "imagined: heart-shape pendant / charm blank"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(25, 50)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        # lobe ratio: lobe radius vs scale
        lobe_ratio = float(rng.uniform(0.45, 0.55))
        return {
            "scale": scale,
            "thickness": thickness,
            "lobe_ratio": lobe_ratio,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 18 and p["thickness"] >= 1.5 and 0.3 <= p["lobe_ratio"] <= 0.7
        )

    def make_program(self, p):
        # Heart shape: two semicircle lobes on top + V bottom.
        # Each lobe is a circle of radius rL centered at (±rL, 0).
        # The bottom V converges from the outer-bottom of each lobe to
        # the bottom point at (0, -L).
        s = p["scale"]
        rL = s * p["lobe_ratio"]
        # Lobe centers at (±rL, 0). Each lobe is a semicircle (top half-circle
        # plus a quarter-circle on the outside).
        # Heart outline (CCW), starting at bottom point (0, -L):
        L = s  # bottom point depth
        # Right side: from bottom (0, -L) up to right edge of right lobe
        # (right lobe bottom-outer corner) — straight line, angle determined by
        # heart geometry. Right lobe is centered at (rL, 0), radius rL.
        # The outer edge of right lobe at the lowest visible point = (2*rL, 0)
        # (right tip of right lobe).
        # Path:
        #   (0, -L) → (2*rL, 0)  [right diagonal of V]
        #   arc from (2*rL, 0) through (rL, rL) to (0, 0) [right lobe top: 180° CCW]
        #   arc from (0, 0) through (-rL, rL) to (-2*rL, 0) [left lobe top: 180° CCW]
        #   (-2*rL, 0) → (0, -L)  [left diagonal of V]
        #   close
        bot = (0, -L)
        right_tip = (2 * rL, 0)
        right_top = (rL, rL)
        center_dip = (0, 0)
        left_top = (-rL, rL)
        left_tip = (-2 * rL, 0)
        ops = [
            Op("moveTo", {"x": _r3(bot[0]), "y": _r3(bot[1])}),
            Op("lineTo", {"x": _r3(right_tip[0]), "y": _r3(right_tip[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(right_top),
                    "point2": _round_pt(center_dip),
                },
            ),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(left_top),
                    "point2": _round_pt(left_tip),
                },
            ),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "heart": True,
                "ref": self.REF,
            },
        )


# 8. simple_plate_with_s_cut — rectangular plate + S-shaped slot cut
class SimplePlateWithSCutFamily(BaseFamily):
    name = "simple_plate_with_s_cut"
    standard = "N/A"
    REF = "imagined: rectangular plate with S-shaped routed channel cut"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(60, 90)), 1)
        W = round(float(rng.uniform(30, 50)), 1)
        T = round(float(rng.uniform(4, 12)), 1)
        # S amplitude limited: must satisfy amp <= L * 0.13 so the arc
        # curvature stays well within OCC's tolerance for the chosen
        # spine x-spread (x_l..x_r = ±0.35 L, crests at ±0.18 L).
        amp = round(L * float(rng.uniform(0.06, 0.12)), 1)
        slot_w = round(W * float(rng.uniform(0.08, 0.13)), 1)
        return {
            "length": L,
            "width": W,
            "thickness": T,
            "amp": amp,
            "slot_w": slot_w,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] >= 40
            and p["width"] >= 25
            and p["thickness"] >= 2
            and p["amp"] >= 3
            and p["amp"] <= p["length"] * 0.13
            and p["slot_w"] >= 2
            and 2 * p["amp"] + p["slot_w"] < p["width"] - 4
            and p["slot_w"] < p["amp"]  # slot narrower than amplitude
            and p["slot_w"] < p["length"] / 4
        )

    def make_program(self, p):
        # Plate + S-shaped slot cut.  The slot uses 4 threePointArcs (2 above
        # spine, 2 below) instead of polyline-offset (which produces wires
        # OCC's offset/cut machinery rejects).
        L = p["length"]
        W = p["width"]
        T = p["thickness"]
        amp = p["amp"]
        sw = p["slot_w"]

        x_l = -L * 0.35
        x_r = +L * 0.35
        # Crest x-positions for top/bottom arcs of S spine
        x_top = -L * 0.18
        x_bot = +L * 0.18

        ops = [
            # Plate
            Op("rect", {"length": L, "width": W}),
            Op("extrude", {"distance": T}),
            # S-cut on top face (closed wire built from 4 arcs + 2 short joins)
            Op("workplane", {"selector": ">Z"}),
            Op("moveTo", {"x": _r3(x_l), "y": _r3(sw / 2.0)}),
            # Outer top edge: arc over crest at (+amp + sw/2)
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((x_top, amp + sw / 2.0)),
                    "point2": _round_pt((0.0, sw / 2.0)),
                },
            ),
            # Outer bottom edge: arc under trough at (-amp + sw/2)
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((x_bot, -amp + sw / 2.0)),
                    "point2": _round_pt((x_r, sw / 2.0)),
                },
            ),
            # Step down to inner edge at right tip
            Op("lineTo", {"x": _r3(x_r), "y": _r3(-sw / 2.0)}),
            # Inner bottom edge (return): arc under trough at (-amp - sw/2)
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((x_bot, -amp - sw / 2.0)),
                    "point2": _round_pt((0.0, -sw / 2.0)),
                },
            ),
            # Inner top edge (return): arc over crest at (+amp - sw/2)
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((x_top, amp - sw / 2.0)),
                    "point2": _round_pt((x_l, -sw / 2.0)),
                },
            ),
            Op("close", {}),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "s_cut": True,
                "ref": self.REF,
            },
        )


# 9. simple_question_mark_plate — top arc + drop + bottom dot
class SimpleQuestionMarkPlateFamily(BaseFamily):
    name = "simple_question_mark_plate"
    standard = "N/A"
    REF = "imagined: extruded question-mark sign / icon"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(25, 45)), 1)
        stroke = round(scale * float(rng.uniform(0.18, 0.25)), 1)
        gap_deg = float(rng.choice([60.0, 80.0, 100.0]))
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "scale": scale,
            "stroke": stroke,
            "gap_deg": gap_deg,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 20
            and p["stroke"] >= 4
            and p["stroke"] < p["scale"] * 0.35
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Question mark = arc on top (3/4 circle opening to lower-right) +
        # a vertical drop + a small dot below.
        # We'll build TWO separate extrude features: the curved hook+drop
        # outline (single closed wire), then a separate disc for the dot.
        # But we're constrained to sketch-first single-extrude. So we instead
        # build the hook+drop as ONE extrude, and add the dot as a SEPARATE
        # union via a second sketch+extrude (this is still sketch-first per
        # feature; it's two sequential sketch+extrudes which is permitted by
        # the rules of "no multi-stage extrudes" — actually that says NO. So
        # we'll combine: do the hook-with-drop, then a top-face workplane +
        # circle + small extrude UPWARD on top of the existing plate. But
        # that's a second extrude on a face... easier: we just include the
        # dot as part of the SAME closed sketch by connecting it via a thin
        # bridge to the drop. That's ugly.
        # Cleanest: drop the dot. Just build "?" without the dot — the hook
        # alone is already recognizable as a question-mark shape.
        s = p["scale"]
        w = p["stroke"]
        gap = math.radians(p["gap_deg"])
        # Hook is a C-shape opening to LOWER-RIGHT, with stroke width w.
        # Outer radius = s/2 + w/2, inner = s/2 - w/2.
        ro = s / 2.0 + w / 2.0
        ri = s / 2.0 - w / 2.0
        # Hook center = (0, +s/2). Gap centered around angle = -π/4 (lower-right).
        cx, cy = 0.0, s / 2.0
        gap_center = -math.pi / 4
        a0 = gap_center + gap / 2.0  # outer arc start (one side of gap)
        # outer arc end (other side of the gap, mod 2π): gap_center - gap/2.
        # outer arc through-pt at angle = π - π/4 = 3π/4 (back-left of hook)
        outer_through_a = math.pi - math.pi / 4  # 3π/4
        # Drop: from inner-end of arc (at angle a1, which is gap_center - gap/2 + 2π,
        # i.e. effectively gap_center - gap/2), drop straight downward by drop_len.
        # Actually we want the drop to extend BELOW the hook to make a "?" shape.
        # End of outer hook (at a1 mod 2π = gap_center - gap/2) is in lower-right
        # area. From there, drop downward to bottom of question mark.
        drop_len = s * 0.7

        outer_start = (cx + ro * math.cos(a0), cy + ro * math.sin(a0))
        outer_through = (
            cx + ro * math.cos(outer_through_a),
            cy + ro * math.sin(outer_through_a),
        )
        a1_mod = gap_center - gap / 2.0  # equivalent angle mod 2π
        outer_end = (cx + ro * math.cos(a1_mod), cy + ro * math.sin(a1_mod))
        inner_end = (cx + ri * math.cos(a1_mod), cy + ri * math.sin(a1_mod))
        inner_through = (
            cx + ri * math.cos(outer_through_a),
            cy + ri * math.sin(outer_through_a),
        )
        inner_start = (cx + ri * math.cos(a0), cy + ri * math.sin(a0))

        # Drop bottom: extend from outer_end straight down by drop_len.
        # Drop is a vertical bar of width = w aligned with the tangent at a1.
        # Simplification: drop is vertical, top-aligned with outer_end / inner_end
        # at their current x-positions. Width = inner_end.x - outer_end.x?
        # That's the radial thickness. But for a clean drop bar we want a
        # rectangular vertical bar of width = w aligned in the radial direction
        # at angle a1.
        # tangent at a1_mod: (-sin(a1_mod), cos(a1_mod))
        # We extend from outer_end and inner_end in the tangent direction
        # (downward) by drop_len.
        tan_x = -math.sin(a1_mod)
        tan_y = math.cos(a1_mod)
        # Want drop to point DOWNWARD (-y direction). At a1_mod ~ -π/4,
        # tan = (-sin(-π/4), cos(-π/4)) = (√2/2, √2/2) — upper right. Wrong direction.
        # Reverse the tangent so the drop goes "outward away from arc center" —
        # actually we want the drop direction to match the natural extension of
        # the hook stroke. The hook ends with the stroke heading roughly toward
        # +x, +y direction (going CCW around the hook). To extend "downward" for
        # a question-mark drop, we go in the OPPOSITE direction: (-tan_x, -tan_y).
        drop_dir_x = -tan_x
        drop_dir_y = -tan_y
        drop_outer_bot = (
            outer_end[0] + drop_len * drop_dir_x,
            outer_end[1] + drop_len * drop_dir_y,
        )
        drop_inner_bot = (
            inner_end[0] + drop_len * drop_dir_x,
            inner_end[1] + drop_len * drop_dir_y,
        )

        ops = [
            # Hook outline + drop, traversed CCW
            Op("moveTo", {"x": _r3(outer_start[0]), "y": _r3(outer_start[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(outer_through),
                    "point2": _round_pt(outer_end),
                },
            ),
            Op("lineTo", {"x": _r3(drop_outer_bot[0]), "y": _r3(drop_outer_bot[1])}),
            Op("lineTo", {"x": _r3(drop_inner_bot[0]), "y": _r3(drop_inner_bot[1])}),
            Op("lineTo", {"x": _r3(inner_end[0]), "y": _r3(inner_end[1])}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(inner_through),
                    "point2": _round_pt(inner_start),
                },
            ),
            Op("close", {}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "letter": "?",
                "ref": self.REF,
            },
        )


# 10. simple_yin_yang_plate — disc + S-curve groove + 2 small holes
class SimpleYinYangPlateFamily(BaseFamily):
    name = "simple_yin_yang_plate"
    standard = "N/A"
    REF = "imagined: taiji / yin-yang medallion (disc + S-groove + dots)"

    def sample_params(self, difficulty, rng):
        r = round(float(rng.uniform(25, 40)), 1)
        thickness = round(float(rng.uniform(5, 14)), 1)
        groove_w = round(r * float(rng.uniform(0.05, 0.10)), 1)
        groove_depth = round(thickness * float(rng.uniform(0.3, 0.5)), 1)
        dot_r = round(r * float(rng.uniform(0.10, 0.14)), 1)
        return {
            "r_disc": r,
            "thickness": thickness,
            "groove_w": groove_w,
            "groove_depth": groove_depth,
            "dot_r": dot_r,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_disc"] >= 18
            and p["thickness"] >= 3
            and p["groove_w"] >= 1.5
            and p["groove_depth"] > 0
            and p["groove_depth"] < p["thickness"]
            and p["dot_r"] >= 2
            and p["dot_r"] < p["r_disc"] * 0.25
        )

    def make_program(self, p):
        rd = p["r_disc"]
        T = p["thickness"]
        gw = p["groove_w"]
        gd = p["groove_depth"]
        dr = p["dot_r"]

        # S-curve dividing line: spine from (0, +rd) to (0, -rd) traversing
        # through right-half of upper half (around (0, +rd/2)) and left-half
        # of lower half (around (0, -rd/2)).
        # Spine = top semicircle (center (0, rd/2), radius rd/2, angle π → 0
        # going CW, i.e. from (-rd/2, rd/2) through top (0, rd) to (rd/2, rd/2))
        # — NO, top of S-curve in yin-yang goes from (0, rd) on the disc edge
        # to (0, 0) center. It's a semicircle of radius rd/2 centered at (0, rd/2).
        # Then bottom half: semicircle radius rd/2 centered at (0, -rd/2),
        # from (0, 0) to (0, -rd).
        # Spine sample:
        spine = []
        n_arc = 30
        # Top half: from (0, rd) angle = π/2 (top of small circle), going CW
        # (decreasing angle) to (0, 0) angle = -π/2 (bottom of small circle).
        # Center (0, rd/2), radius rd/2.
        for i in range(n_arc + 1):
            t = math.pi / 2 - (i / n_arc) * math.pi  # π/2 → -π/2
            x = (rd / 2.0) * math.cos(t)
            y = rd / 2.0 + (rd / 2.0) * math.sin(t)
            spine.append((x, y))
        # Bottom half: from (0, 0) to (0, -rd). Center (0, -rd/2), radius rd/2.
        # From angle π/2 (top of circle = (0, 0)) going CCW to angle 3π/2 = -π/2
        # (bottom of circle = (0, -rd)). CCW = increasing angle.
        for i in range(1, n_arc + 1):
            t = math.pi / 2 + (i / n_arc) * math.pi  # π/2 → 3π/2
            x = (rd / 2.0) * math.cos(t)
            y = -rd / 2.0 + (rd / 2.0) * math.sin(t)
            spine.append((x, y))

        # Offset spine by ±gw/2 to form a closed groove polyline.
        def offset_curve(pts, off):
            out = []
            for k in range(len(pts)):
                if k == 0:
                    dx = pts[1][0] - pts[0][0]
                    dy = pts[1][1] - pts[0][1]
                elif k == len(pts) - 1:
                    dx = pts[-1][0] - pts[-2][0]
                    dy = pts[-1][1] - pts[-2][1]
                else:
                    dx = pts[k + 1][0] - pts[k - 1][0]
                    dy = pts[k + 1][1] - pts[k - 1][1]
                m = math.hypot(dx, dy) or 1e-9
                nx = -dy / m
                ny = dx / m
                out.append((pts[k][0] + off * nx, pts[k][1] + off * ny))
            return out

        outer = offset_curve(spine, +gw / 2.0)
        inner = offset_curve(spine, -gw / 2.0)
        groove_outline = outer + list(reversed(inner))
        groove_outline = [_round_pt(p_) for p_ in groove_outline]

        ops = [
            # Disc
            Op("circle", {"radius": rd}),
            Op("extrude", {"distance": T}),
            # Groove cut on top face (blind, half thickness)
            Op("workplane", {"selector": ">Z"}),
            Op("polyline", {"points": groove_outline}),
            Op("close", {}),
            Op("cutBlind", {"depth": gd}),
            # Two small dots: one in upper half, one in lower half
            Op("workplane", {"selector": ">Z"}),
            Op(
                "pushPoints",
                {"points": [(0.0, _r3(rd / 2.0)), (0.0, _r3(-rd / 2.0))]},
            ),
            Op("hole", {"diameter": 2 * dr}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "yin_yang": True,
                "sketch_arc": True,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


ALL_FAMILIES = [
    SimpleLetterSPlateFamily,
    SimpleLetterCPlateFamily,
    SimpleLetterGPlateFamily,
    SimpleSmileyPlateFamily,
    SimpleHollowKeyPlateFamily,
    SimpleCurvedArrowPlateFamily,
    SimpleHeartPlateFamily,
    SimplePlateWithSCutFamily,
    SimpleQuestionMarkPlateFamily,
    SimpleYinYangPlateFamily,
]
