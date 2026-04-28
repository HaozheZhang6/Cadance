"""simple_arc_profiles_pack — 8 arc-based 2D-extrude families.

Companion to simple_profiles_pack: covers common arc / arc+line profiles
that are everywhere in real CAD but were missing from the polyline-only pack.

All families: build a closed sketch in XY, then a single .extrude(thickness).
Most produce thin plates (thickness < 30 mm).

Op vocabulary used (verified in pipeline/builder.py):
  - Op("ellipse", {"xRadius","yRadius"})            true ellipse primitive
  - Op("moveTo", {"x","y"})                         pen-down at start of arc
  - Op("threePointArc", {"point1","point2"})        through-pt, end-pt
  - Op("lineTo", {"x","y"}), Op("close",{}), Op("extrude",{"distance"})

Family list:
  simple_oval_plate          true ellipse → thin plate
  simple_tear_drop_plate     round head + triangular tail (1 arc + 2 lines)
  simple_tab_plate           rect with ONE rounded end (2 lines + 1 arc + 1 line)
  simple_lobe_plate          semicircle head + rect handle (1 arc + 3 lines)
  simple_lens_plate          2 arcs back-to-back (vesica piscis / eye)
  simple_arc_bar_plate       thick curved bar (banana/rainbow: 2 arcs + 2 chords)
  simple_ring_segment_plate  annular sector / donut wedge (2 arcs + 2 radial)
  simple_arc_corner_bracket  L-bracket with rounded inner corner (stress relief)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- shared helpers --------------------------------------------------


def _arc_mid(cx, cy, r, a0, a1):
    """Mid-point of arc from angle a0 to a1 around (cx,cy) with radius r."""
    am = (a0 + a1) / 2.0
    return (cx + r * math.cos(am), cy + r * math.sin(am))


def _r3(x):
    return round(float(x), 3)


def _round_pt(p):
    return (_r3(p[0]), _r3(p[1]))


# ---------- families --------------------------------------------------------


# 1. simple_oval_plate — true ellipse
class SimpleOvalPlateFamily(BaseFamily):
    name = "simple_oval_plate"
    standard = "N/A"
    REF = "imagined: oval cover plate / gasket blank"

    def sample_params(self, difficulty, rng):
        major = round(float(rng.uniform(30, 60)), 1)
        # ratio 1.3 .. 3.0
        ratio = float(rng.uniform(1.3, 3.0))
        minor = round(major / ratio, 1)
        thickness = round(float(rng.uniform(2, 12)), 1)
        return {
            "major": major,
            "minor": minor,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["major"] > p["minor"] + 1.5 and p["minor"] >= 5 and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        ops = [
            Op("ellipse", {"xRadius": p["major"], "yRadius": p["minor"]}),
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
                "ref": self.REF,
            },
        )


# 2. simple_tear_drop_plate — round head (semicircle) + triangular tail
class SimpleTearDropPlateFamily(BaseFamily):
    name = "simple_tear_drop_plate"
    standard = "N/A"
    REF = "imagined: water-droplet hanger tag / fairing cross-section"

    def sample_params(self, difficulty, rng):
        head_r = round(float(rng.uniform(10, 25)), 1)
        # tail length 1.5..3x head radius
        tail_len = round(head_r * float(rng.uniform(1.5, 3.0)), 1)
        thickness = round(float(rng.uniform(2, 10)), 1)
        return {
            "head_r": head_r,
            "tail_len": tail_len,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["head_r"] >= 5 and p["tail_len"] >= p["head_r"] and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Head: circle of radius head_r centered at origin.
        # We use the head as a 270° arc from (0, -r) → (r, 0) → (0, r) → (-r, 0)
        # then 2 lines from (-r,0) → tip → (0, -r) ... wait that's wrong.
        # Easier: 270° arc on left side; tail tip on right.
        #   start at (0, head_r)  [top of circle]
        #   arc through (-head_r, 0) [leftmost] to (0, -head_r) [bottom]
        #   line to (tail_len, 0) [tip]
        #   line back to (0, head_r) [top]  → close
        r = p["head_r"]
        tip_x = r + p["tail_len"]
        ops = [
            Op("moveTo", {"x": _r3(0), "y": _r3(r)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((-r, 0)),
                    "point2": _round_pt((0, -r)),
                },
            ),
            Op("lineTo", {"x": _r3(tip_x), "y": _r3(0)}),
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
                "ref": self.REF,
            },
        )


# 3. simple_tab_plate — rect with ONE rounded end (semi-stadium)
class SimpleTabPlateFamily(BaseFamily):
    name = "simple_tab_plate"
    standard = "N/A"
    REF = "imagined: hangar tab / mounting tab with single rounded end"

    def sample_params(self, difficulty, rng):
        width = round(float(rng.uniform(15, 35)), 1)
        # rect length excluding round end
        rect_len = round(width * float(rng.uniform(1.0, 2.5)), 1)
        thickness = round(float(rng.uniform(2, 10)), 1)
        return {
            "width": width,
            "rect_len": rect_len,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["width"] >= 8 and p["rect_len"] >= 8 and p["thickness"] >= 1.5

    def make_program(self, p):
        # Plate centered at origin. Square end at x=0 (left), rounded at x=rect_len (right).
        # Half-width r = width/2.
        # Path:  (0, -r) → lineTo (rect_len, -r) → arc through (rect_len+r, 0)
        #        to (rect_len, r) → lineTo (0, r) → close
        r = p["width"] / 2.0
        L = p["rect_len"]
        ops = [
            Op("moveTo", {"x": _r3(0), "y": _r3(-r)}),
            Op("lineTo", {"x": _r3(L), "y": _r3(-r)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((L + r, 0)),
                    "point2": _round_pt((L, r)),
                },
            ),
            Op("lineTo", {"x": _r3(0), "y": _r3(r)}),
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
                "ref": self.REF,
            },
        )


# 4. simple_lobe_plate — semicircle head + rectangular handle
class SimpleLobePlateFamily(BaseFamily):
    name = "simple_lobe_plate"
    standard = "N/A"
    REF = "imagined: paddle / fat key tab / spatula tip"

    def sample_params(self, difficulty, rng):
        head_r = round(float(rng.uniform(12, 28)), 1)
        # handle width narrower than head diameter
        handle_w = round(head_r * float(rng.uniform(0.5, 0.95)), 1)
        handle_len = round(head_r * float(rng.uniform(1.2, 2.5)), 1)
        thickness = round(float(rng.uniform(2, 10)), 1)
        return {
            "head_r": head_r,
            "handle_w": handle_w,
            "handle_len": handle_len,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["head_r"] >= 6
            and p["handle_w"] < 2 * p["head_r"]
            and p["handle_len"] >= 6
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Head = semicircle of radius head_r, flat side on the y-axis
        # (head extends to +x). Handle rect extends to -x.
        # Half-handle = handle_w/2 = hw.
        # Path (CCW):
        #   (0, hw) → arc through (head_r, 0) to (0, -hw)
        #   line to (-handle_len, -hw)
        #   line to (-handle_len, hw)
        #   close
        r = p["head_r"]
        hw = p["handle_w"] / 2.0
        L = p["handle_len"]
        # arc start (0, hw), end (0, -hw); through point on +x side at distance r from origin
        # but the chord is from (0,hw) to (0,-hw), midpoint of arc on +x side along the
        # perpendicular bisector → (sqrt(r^2 - hw^2), 0) if hw < r,
        # otherwise just use (r, 0) as a fallback (we validate hw < r in validate_params via 2r).
        # Actually we want the head to be a full half-circle of radius head_r ignoring hw.
        # Then handle attaches via straight cuts on the chord at +/-hw.
        # The arc from (0, hw) → (0, -hw) on the head_r-radius circle goes through (head_r, 0).
        # That requires hw <= r, which we enforce in validate_params (handle_w < 2*head_r means
        # hw < head_r). Good.
        through_x = math.sqrt(max(0.001, r * r - hw * hw))
        ops = [
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
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 5. simple_lens_plate — 2 arcs back-to-back (vesica piscis / eye)
class SimpleLensPlateFamily(BaseFamily):
    name = "simple_lens_plate"
    standard = "N/A"
    REF = "imagined: lens / vesica piscis / eye-shaped gasket"

    def sample_params(self, difficulty, rng):
        # Lens defined by half-length L (along x) and half-height H (along y).
        # Each arc has radius R = (L^2 + H^2) / (2H) and is centered offset
        # along ±y so the arc passes through (-L,0), (0,H), (L,0) (top arc)
        # and (-L,0), (0,-H), (L,0) (bottom arc).
        L = round(float(rng.uniform(20, 45)), 1)
        # height ratio: 0.3 (slim eye) .. 0.85 (almost-circle)
        ratio = float(rng.uniform(0.3, 0.85))
        H = round(L * ratio, 1)
        thickness = round(float(rng.uniform(2, 10)), 1)
        return {
            "half_length": L,
            "half_height": H,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["half_length"] >= 6
            and p["half_height"] >= 3
            and p["half_height"] < p["half_length"]
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        L = p["half_length"]
        H = p["half_height"]
        # Path (CCW):
        #   start at (-L, 0)
        #   arc through (0, H) to (L, 0)        [top arc]
        #   arc through (0, -H) to (-L, 0)      [bottom arc]
        #   close
        ops = [
            Op("moveTo", {"x": _r3(-L), "y": _r3(0)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((0, H)),
                    "point2": _round_pt((L, 0)),
                },
            ),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((0, -H)),
                    "point2": _round_pt((-L, 0)),
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
                "ref": self.REF,
            },
        )


# 6. simple_arc_bar_plate — banana / rainbow shape (2 concentric arcs + 2 chords)
class SimpleArcBarPlateFamily(BaseFamily):
    name = "simple_arc_bar_plate"
    standard = "N/A"
    REF = "imagined: banana clamp / curved guide rail / rainbow bar"

    def sample_params(self, difficulty, rng):
        # Mean radius and bar thickness; arc sweep angle.
        r_mean = round(float(rng.uniform(25, 50)), 1)
        bar_t = round(r_mean * float(rng.uniform(0.15, 0.35)), 1)
        sweep_deg = float(rng.choice([60.0, 90.0, 120.0, 150.0]))
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "r_mean": r_mean,
            "bar_t": bar_t,
            "sweep_deg": sweep_deg,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_mean"] > p["bar_t"] + 4
            and p["bar_t"] >= 4
            and 30 <= p["sweep_deg"] <= 270
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        r_outer = p["r_mean"] + p["bar_t"] / 2.0
        r_inner = p["r_mean"] - p["bar_t"] / 2.0
        sweep = math.radians(p["sweep_deg"])
        # Center the sweep symmetrically around +x axis: a0 = -sweep/2, a1 = +sweep/2
        a0 = -sweep / 2.0
        a1 = +sweep / 2.0
        am = 0.0  # mid-arc angle
        # outer arc start (a0) → mid (am) → end (a1)
        outer_start = (r_outer * math.cos(a0), r_outer * math.sin(a0))
        outer_mid = (r_outer * math.cos(am), r_outer * math.sin(am))
        outer_end = (r_outer * math.cos(a1), r_outer * math.sin(a1))
        # inner arc end → mid → start (we walk it backwards, a1 → am → a0)
        inner_end = (r_inner * math.cos(a1), r_inner * math.sin(a1))
        inner_mid = (r_inner * math.cos(am), r_inner * math.sin(am))
        inner_start = (r_inner * math.cos(a0), r_inner * math.sin(a0))
        # Path (CCW):
        #   moveTo outer_start
        #   arc(outer_mid → outer_end)        [outer arc, CCW]
        #   lineTo inner_end                  [radial chord at a1]
        #   arc(inner_mid → inner_start)      [inner arc, CW relative to center]
        #   lineTo outer_start                [radial chord at a0]  (close handles this)
        ops = [
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
                "ref": self.REF,
            },
        )


# 7. simple_ring_segment_plate — annular sector (donut wedge)
class SimpleRingSegmentPlateFamily(BaseFamily):
    name = "simple_ring_segment_plate"
    standard = "N/A"
    REF = "imagined: ring sector / sliced washer / pie-cut spacer"

    def sample_params(self, difficulty, rng):
        r_outer = round(float(rng.uniform(25, 50)), 1)
        r_inner = round(r_outer * float(rng.uniform(0.4, 0.8)), 1)
        sweep_deg = float(rng.choice([45.0, 60.0, 90.0, 120.0, 150.0, 180.0]))
        thickness = round(float(rng.uniform(2, 12)), 1)
        return {
            "r_outer": r_outer,
            "r_inner": r_inner,
            "sweep_deg": sweep_deg,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_outer"] > p["r_inner"] + 3
            and p["r_inner"] >= 4
            and 20 <= p["sweep_deg"] <= 300
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        ro = p["r_outer"]
        ri = p["r_inner"]
        sweep = math.radians(p["sweep_deg"])
        # Sector centered around +x axis from a0 to a1
        a0 = -sweep / 2.0
        a1 = +sweep / 2.0
        am = 0.0
        outer_start = (ro * math.cos(a0), ro * math.sin(a0))
        outer_mid = (ro * math.cos(am), ro * math.sin(am))
        outer_end = (ro * math.cos(a1), ro * math.sin(a1))
        inner_end = (ri * math.cos(a1), ri * math.sin(a1))
        inner_mid = (ri * math.cos(am), ri * math.sin(am))
        inner_start = (ri * math.cos(a0), ri * math.sin(a0))
        # Same topology as arc_bar but with ri/ro independent (not r_mean ± t/2).
        ops = [
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
                "ref": self.REF,
            },
        )


# 8. simple_arc_corner_bracket — L-bracket with rounded INNER corner
class SimpleArcCornerBracketFamily(BaseFamily):
    name = "simple_arc_corner_bracket"
    standard = "N/A"
    REF = "imagined: stress-relief L-bracket with curved fillet inner corner"

    def sample_params(self, difficulty, rng):
        leg_a = round(float(rng.uniform(30, 70)), 1)
        leg_b = round(float(rng.uniform(30, 70)), 1)
        # leg width (thickness of each leg as drawn in the 2D outline)
        leg_w = round(float(rng.uniform(8, 16)), 1)
        # inner fillet radius < min(leg_a, leg_b) - leg_w
        max_fr = min(leg_a, leg_b) - leg_w - 2
        fillet_r = round(float(rng.uniform(4, max(5, max_fr * 0.6))), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "leg_a": leg_a,
            "leg_b": leg_b,
            "leg_w": leg_w,
            "fillet_r": fillet_r,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["leg_a"] >= p["leg_w"] + p["fillet_r"] + 4
            and p["leg_b"] >= p["leg_w"] + p["fillet_r"] + 4
            and p["leg_w"] >= 4
            and p["fillet_r"] >= 2
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        a = p["leg_a"]  # horizontal leg length (along +x)
        b = p["leg_b"]  # vertical leg length (along +y)
        w = p["leg_w"]  # leg width
        fr = p["fillet_r"]  # inner corner fillet radius
        # 2D L-shape with inner corner rounded by an arc of radius fr.
        # Outline (CCW), starting at outer corner (0,0):
        #   (0, 0) → (a, 0)       [bottom of horizontal leg]
        #   (a, 0) → (a, w)       [right end of horizontal leg]
        #   (a, w) → (w + fr, w)  [top of horizontal leg up to start of fillet]
        #   arc from (w + fr, w) through (w + fr - fr*cos(45), w + fr - fr*sin(45))
        #     ... actually the fillet is a quarter-arc with center at (w + fr, w + fr).
        #   end of arc: (w, w + fr)
        #   (w, w + fr) → (w, b)  [right side of vertical leg]
        #   (w, b) → (0, b)       [top of vertical leg]
        #   close to (0, 0)
        # Inner-corner fillet center = (w + fr, w + fr); arc goes from
        # (w + fr, w) [angle = -π/2 from center] → (w, w + fr) [angle = π from center]
        # CCW around the center (since outline is CCW around the L body, the
        # fillet bulges INTO the inner corner = arc center on the far side).
        cx = w + fr
        cy = w + fr
        # Arc from angle -π/2 (start, point (cx, cy - fr) = (w + fr, w))
        # to angle π (end, point (cx - fr, cy) = (w, w + fr)),
        # going CCW = passing through angle ≈ -π/2 → π via 3π/4? No: -π/2 → π CCW
        # crosses π/2 (top) and π (left), but we want the arc to bulge INTO the
        # corner (toward origin). The arc through angle 3π/4 (point at upper-left
        # of center) faces origin. Let's parametrize:
        #   start angle θs = -π/2 → (cx, cy-fr) = (w+fr, w)              ✓
        #   end angle   θe = π    → (cx-fr, cy) = (w, w+fr)              ✓
        # The CCW path from -π/2 to π sweeps 3π/2 around the FAR side (bulges
        # away from origin) — wrong.  The CW path from -π/2 to π sweeps π/2 and
        # bulges toward origin — that's what we want.  threePointArc just needs
        # the through-point; specify the through-point in the "toward origin"
        # half so OCC builds the short (CW-around-center) arc.
        # Through-point: angle = (-π/2 + π)/2 = π/4 from center?  No; we want
        # the SHORT arc, so through-point should be at angle 5π/4 or
        # equivalently -3π/4 (between -π/2 going CW to π, the midpoint is at
        # angle -3π/4 from center, which is the lower-left of center →
        # toward origin).  Point: (cx + fr·cos(-3π/4), cy + fr·sin(-3π/4))
        #               = (cx - fr/√2, cy - fr/√2)
        through = (cx - fr / math.sqrt(2), cy - fr / math.sqrt(2))
        ops = [
            Op("moveTo", {"x": _r3(0), "y": _r3(0)}),
            Op("lineTo", {"x": _r3(a), "y": _r3(0)}),
            Op("lineTo", {"x": _r3(a), "y": _r3(w)}),
            Op("lineTo", {"x": _r3(w + fr), "y": _r3(w)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt(through),
                    "point2": _round_pt((w, w + fr)),
                },
            ),
            Op("lineTo", {"x": _r3(w), "y": _r3(b)}),
            Op("lineTo", {"x": _r3(0), "y": _r3(b)}),
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
                "has_fillet_corner": True,
                "ref": self.REF,
            },
        )


ALL_FAMILIES = [
    SimpleOvalPlateFamily,
    SimpleTearDropPlateFamily,
    SimpleTabPlateFamily,
    SimpleLobePlateFamily,
    SimpleLensPlateFamily,
    SimpleArcBarPlateFamily,
    SimpleRingSegmentPlateFamily,
    SimpleArcCornerBracketFamily,
]
