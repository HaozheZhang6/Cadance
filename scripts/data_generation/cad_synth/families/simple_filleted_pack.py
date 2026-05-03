"""simple_filleted_pack — polyline + corner fillet + extrude families.

Pattern: build a closed polyline with sharp vertices, extrude, then
.edges("|Z").fillet(r) to round all vertical corner-edges. Result is a
prism with an organic / die-cut silhouette.

Distinct from:
- simple_arc_profiles_pack — single curved-arc shapes
- simple_symbol_pack — letter/symbol silhouettes
- simple_profiles_pack — mostly sharp polylines (this pack always fillets)

Family list:
  simple_filleted_l_plate        — L-shape, 6 verts filleted
  simple_filleted_t_plate        — T-shape, 8 verts filleted
  simple_filleted_u_plate        — U-shape, 8 verts filleted
  simple_filleted_cross_plate    — Plus shape, 12 verts filleted
  simple_filleted_step_plate     — staircase profile, N steps
  simple_filleted_zigzag_plate   — zigzag bar with rounded peaks
  simple_filleted_hexagon_plate  — hex polygon, vertex fillets
  simple_filleted_octagon_plate  — oct polygon, vertex fillets
  simple_filleted_arrow_plate    — arrow with rounded corners
  simple_filleted_chevron_plate  — chevron with rounded corners
  simple_filleted_dumbbell_plate — 2 bulges + waist, concave corners filleted
  simple_filleted_ribbon_plate   — long ribbon with cut-corner notches
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- polyline generators -------------------------------------------


def _l_pts(leg_a, leg_b, leg_w):
    """L-shape: legs along +X (length leg_a) and +Y (length leg_b), thickness leg_w."""
    return [
        (0, 0),
        (leg_a, 0),
        (leg_a, leg_w),
        (leg_w, leg_w),
        (leg_w, leg_b),
        (0, leg_b),
    ]


def _t_pts(span, stem_h, bar_t, stem_w):
    """T-shape: top bar of length span+thickness bar_t, stem going down stem_h x stem_w."""
    return [
        (-span / 2, stem_h),
        (span / 2, stem_h),
        (span / 2, stem_h - bar_t),
        (stem_w / 2, stem_h - bar_t),
        (stem_w / 2, 0),
        (-stem_w / 2, 0),
        (-stem_w / 2, stem_h - bar_t),
        (-span / 2, stem_h - bar_t),
    ]


def _u_pts(span, height, wall_t, base_t):
    """U-shape: outer bbox span x height, walls of thickness wall_t, base thickness base_t."""
    return [
        (0, 0),
        (span, 0),
        (span, height),
        (span - wall_t, height),
        (span - wall_t, base_t),
        (wall_t, base_t),
        (wall_t, height),
        (0, height),
    ]


def _cross_pts(span, arm_t):
    """Plus shape with arm width arm_t and total span = span. 12 vertices."""
    return [
        (-arm_t / 2, -span / 2),
        (arm_t / 2, -span / 2),
        (arm_t / 2, -arm_t / 2),
        (span / 2, -arm_t / 2),
        (span / 2, arm_t / 2),
        (arm_t / 2, arm_t / 2),
        (arm_t / 2, span / 2),
        (-arm_t / 2, span / 2),
        (-arm_t / 2, arm_t / 2),
        (-span / 2, arm_t / 2),
        (-span / 2, -arm_t / 2),
        (-arm_t / 2, -arm_t / 2),
    ]


def _step_pts(n_steps, step_w, step_h, base_h):
    """Staircase: n_steps rising up-right from (0,0). Returns closed polyline."""
    pts = [(0, 0)]
    # rise stair-step from x=0 to x=n_steps*step_w
    x, y = 0.0, 0.0
    for _ in range(n_steps):
        x += step_w
        pts.append((x, y))
        y += step_h
        pts.append((x, y))
    # top-right corner
    total_w = n_steps * step_w
    total_h = n_steps * step_h
    # add top-left and back down to (0, base_h)? No — a clean profile:
    # go up-right staircase, then top edge across, then back down at left
    pts.append((total_w, total_h + base_h))
    pts.append((0, total_h + base_h))
    return pts


def _zigzag_pts(length, n_zigs, amp, base_h):
    """Zigzag bar: top edge zig-zags, bottom edge flat at y=0."""
    pts = [(0, 0)]
    # top edge zigzag from (0, base_h) to (length, base_h)
    pts.append((0, base_h))
    n_pts = n_zigs * 2
    for i in range(1, n_pts):
        x = length * i / n_pts
        y = base_h + (amp if i % 2 == 1 else -amp / 2)
        pts.append((x, y))
    pts.append((length, base_h))
    pts.append((length, 0))
    return pts


def _polygon_pts(n, r):
    return [
        (
            r * math.cos(2 * math.pi * i / n + math.pi / 2),
            r * math.sin(2 * math.pi * i / n + math.pi / 2),
        )
        for i in range(n)
    ]


def _arrow_pts(length, head_h, head_w, shaft_w):
    """Single-direction arrow pointing +X. 7 vertices."""
    return [
        (0, -shaft_w / 2),
        (length - head_h, -shaft_w / 2),
        (length - head_h, -head_w / 2),
        (length, 0),
        (length - head_h, head_w / 2),
        (length - head_h, shaft_w / 2),
        (0, shaft_w / 2),
    ]


def _chevron_pts(width, height, arm_t):
    """V-arrow chevron with arm thickness."""
    return [
        (0, 0),
        (width / 2, height),
        (width, 0),
        (width - arm_t, 0),
        (width / 2, height - arm_t * 1.5),
        (arm_t, 0),
    ]


def _dumbbell_pts(total_l, bulge_w, waist_w, waist_l):
    """Dumbbell: rect with two square bulges at ends, narrow waist in middle.

    Outline (axis: +X). 12 vertices, all corners are sharp.
    """
    bulge_l = (total_l - waist_l) / 2
    return [
        (0, -bulge_w / 2),
        (bulge_l, -bulge_w / 2),
        (bulge_l, -waist_w / 2),
        (bulge_l + waist_l, -waist_w / 2),
        (bulge_l + waist_l, -bulge_w / 2),
        (total_l, -bulge_w / 2),
        (total_l, bulge_w / 2),
        (bulge_l + waist_l, bulge_w / 2),
        (bulge_l + waist_l, waist_w / 2),
        (bulge_l, waist_w / 2),
        (bulge_l, bulge_w / 2),
        (0, bulge_w / 2),
    ]


def _ribbon_pts(length, width, notch_d):
    """Long rectangle with chevron notch cut into each short end (die-cut ribbon).

    8 vertices. Notch points inward (toward center).
    """
    return [
        (0, 0),
        (notch_d, width / 2),
        (0, width),
        (length, width),
        (length - notch_d, width / 2),
        (length, 0),
    ]


# ---------- helper emitter -------------------------------------------------


def _emit_filleted(pts, thickness, fillet_r):
    """Emit Op chain: polyline + close + extrude + fillet vertical edges."""
    pts_r = [(round(x, 3), round(y, 3)) for x, y in pts]
    ops = [Op("moveTo", {"x": pts_r[0][0], "y": pts_r[0][1]})]
    for x, y in pts_r[1:]:
        ops.append(Op("lineTo", {"x": x, "y": y}))
    ops += [
        Op("close", {}),
        Op("extrude", {"distance": thickness}),
        Op("edges", {"selector": "|Z"}),
        Op("fillet", {"radius": fillet_r}),
    ]
    return ops


def _min_segment_length(pts):
    """Return min adjacent edge length of closed polyline."""
    n = len(pts)
    return min(
        math.hypot(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1])
        for i in range(n)
    )


# ---------- base ----------------------------------------------------------


class _FilletedPolyFamily(BaseFamily):
    """Sketch-first polyline + extrude + edges('|Z').fillet(r). Override _make_pts + _sample_size."""

    standard = "N/A"
    REF = ""

    def _sample_size(self, difficulty, rng):
        raise NotImplementedError

    def _make_pts(self, p):
        raise NotImplementedError

    def _max_fillet_factor(self, p):
        """Override to constrain fillet radius vs. shape-specific min dim."""
        return 0.45  # default: fillet < 45% of min adjacent edge

    def sample_params(self, difficulty, rng):
        p = {"difficulty": difficulty}
        p.update(self._sample_size(difficulty, rng))
        # sample fillet radius scaled to shape min-edge
        try:
            pts = self._make_pts(p)
            min_seg = _min_segment_length(pts)
        except Exception:
            min_seg = 4.0
        cap = max(0.5, min_seg * self._max_fillet_factor(p))
        if difficulty == "easy":
            lo, hi = 0.5, min(cap, 1.5)
        elif difficulty == "medium":
            lo, hi = 0.8, min(cap, 3.0)
        else:  # hard
            lo, hi = 1.0, min(cap, 5.0)
        if hi <= lo:
            hi = lo + 0.3
        p["fillet_r"] = round(float(rng.uniform(lo, hi)), 2)
        return p

    def validate_params(self, p):
        if p.get("thickness", 0) < 1.5:
            return False
        if p.get("fillet_r", 0) < 0.3:
            return False
        try:
            pts = self._make_pts(p)
        except Exception:
            return False
        min_seg = _min_segment_length(pts)
        return p["fillet_r"] < min_seg / 2.0 - 0.05

    def make_program(self, p):
        pts = self._make_pts(p)
        ops = _emit_filleted(pts, p["thickness"], p["fillet_r"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "has_fillet": True,
                "filleted_corners": True,
                "ref": self.REF,
            },
        )


# ---------- families -------------------------------------------------------


# 1. L-plate
class SimpleFilletedLPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_l_plate"
    REF = "imagined: L-bracket flat blank with rounded vertices"

    def _sample_size(self, difficulty, rng):
        a = round(float(rng.uniform(40, 90)), 1)
        return {
            "leg_a": a,
            "leg_b": round(a * float(rng.uniform(0.7, 1.2)), 1),
            "leg_w": round(a * float(rng.uniform(0.2, 0.4)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p):
        return _l_pts(p["leg_a"], p["leg_b"], p["leg_w"])


# 2. T-plate
class SimpleFilletedTPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_t_plate"
    REF = "imagined: T-bracket sheet blank with rounded vertices"

    def _sample_size(self, difficulty, rng):
        span = round(float(rng.uniform(50, 100)), 1)
        return {
            "span": span,
            "stem_h": round(span * float(rng.uniform(0.6, 1.2)), 1),
            "bar_t": round(span * float(rng.uniform(0.2, 0.35)), 1),
            "stem_w": round(span * float(rng.uniform(0.2, 0.4)), 1),
            "thickness": round(float(rng.uniform(3, 9)), 1),
        }

    def _make_pts(self, p):
        return _t_pts(p["span"], p["stem_h"], p["bar_t"], p["stem_w"])


# 3. U-plate
class SimpleFilletedUPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_u_plate"
    REF = "imagined: U-channel flat profile with rounded vertices"

    def _sample_size(self, difficulty, rng):
        span = round(float(rng.uniform(40, 90)), 1)
        return {
            "span": span,
            "height": round(span * float(rng.uniform(0.7, 1.3)), 1),
            "wall_t": round(span * float(rng.uniform(0.15, 0.3)), 1),
            "base_t": round(span * float(rng.uniform(0.15, 0.3)), 1),
            "thickness": round(float(rng.uniform(3, 9)), 1),
        }

    def _make_pts(self, p):
        return _u_pts(p["span"], p["height"], p["wall_t"], p["base_t"])


# 4. Cross / plus plate
class SimpleFilletedCrossPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_cross_plate"
    REF = "imagined: plus-sign tile with rounded corners"

    def _sample_size(self, difficulty, rng):
        span = round(float(rng.uniform(50, 100)), 1)
        return {
            "span": span,
            "arm_t": round(span * float(rng.uniform(0.25, 0.4)), 1),
            "thickness": round(float(rng.uniform(4, 10)), 1),
        }

    def _make_pts(self, p):
        return _cross_pts(p["span"], p["arm_t"])


# 5. Stair-step plate
class SimpleFilletedStepPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_step_plate"
    REF = "imagined: staircase silhouette with rounded inner/outer corners"

    def _sample_size(self, difficulty, rng):
        n = int(rng.choice([2, 3, 4, 5]))
        return {
            "n_steps": n,
            "step_w": round(float(rng.uniform(12, 25)), 1),
            "step_h": round(float(rng.uniform(8, 18)), 1),
            "base_h": round(float(rng.uniform(6, 14)), 1),
            "thickness": round(float(rng.uniform(4, 10)), 1),
        }

    def _make_pts(self, p):
        return _step_pts(p["n_steps"], p["step_w"], p["step_h"], p["base_h"])

    def _max_fillet_factor(self, p):
        # step rises are short — keep fillet very small
        return 0.30


# 6. Zigzag plate
class SimpleFilletedZigzagPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_zigzag_plate"
    REF = "imagined: zigzag bar with rounded peaks/valleys"

    def _sample_size(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(60, 120)), 1),
            "n_zigs": int(rng.choice([3, 4, 5])),
            "amplitude": round(float(rng.uniform(4, 10)), 1),
            "base_h": round(float(rng.uniform(15, 30)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p):
        return _zigzag_pts(p["length"], p["n_zigs"], p["amplitude"], p["base_h"])

    def _max_fillet_factor(self, p):
        return 0.30


# 7. Hexagon plate (vertex-filleted hex)
class SimpleFilletedHexagonPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_hexagon_plate"
    REF = "imagined: hex tile with rounded vertices (soft-corner nut blank)"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(20, 40)), 1),
            "thickness": round(float(rng.uniform(4, 12)), 1),
        }

    def _make_pts(self, p):
        return _polygon_pts(6, p["radius"])


# 8. Octagon plate (vertex-filleted oct)
class SimpleFilletedOctagonPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_octagon_plate"
    REF = "imagined: stop-sign style oct tile with rounded vertices"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(22, 42)), 1),
            "thickness": round(float(rng.uniform(4, 12)), 1),
        }

    def _make_pts(self, p):
        return _polygon_pts(8, p["radius"])


# 9. Arrow plate (rounded-corner arrow)
class SimpleFilletedArrowPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_arrow_plate"
    REF = "imagined: directional arrow placard with rounded vertices"

    def _sample_size(self, difficulty, rng):
        L = round(float(rng.uniform(60, 110)), 1)
        return {
            "length": L,
            "head_h": round(L * float(rng.uniform(0.25, 0.4)), 1),
            "head_w": round(L * float(rng.uniform(0.4, 0.65)), 1),
            "shaft_w": round(L * float(rng.uniform(0.18, 0.3)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p):
        return _arrow_pts(p["length"], p["head_h"], p["head_w"], p["shaft_w"])

    def _max_fillet_factor(self, p):
        return 0.30


# 10. Chevron plate (rounded-corner chevron)
class SimpleFilletedChevronPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_chevron_plate"
    REF = "imagined: military-rank chevron with rounded vertices"

    def _sample_size(self, difficulty, rng):
        w = round(float(rng.uniform(50, 100)), 1)
        return {
            "width": w,
            "height": round(w * float(rng.uniform(0.5, 0.9)), 1),
            "arm_t": round(w * float(rng.uniform(0.15, 0.25)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p):
        return _chevron_pts(p["width"], p["height"], p["arm_t"])

    def _max_fillet_factor(self, p):
        return 0.30


# 11. Dumbbell plate
class SimpleFilletedDumbbellPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_dumbbell_plate"
    REF = "imagined: dumbbell silhouette — two end blocks + narrow waist, rounded"

    def _sample_size(self, difficulty, rng):
        L = round(float(rng.uniform(80, 140)), 1)
        bulge = round(L * float(rng.uniform(0.3, 0.45)), 1)
        return {
            "total_l": L,
            "bulge_w": bulge,
            "waist_w": round(bulge * float(rng.uniform(0.35, 0.6)), 1),
            "waist_l": round(L * float(rng.uniform(0.3, 0.5)), 1),
            "thickness": round(float(rng.uniform(4, 10)), 1),
        }

    def _make_pts(self, p):
        return _dumbbell_pts(p["total_l"], p["bulge_w"], p["waist_w"], p["waist_l"])

    def _max_fillet_factor(self, p):
        # waist depth is small — limit fillet to avoid overlap
        bulge = p.get("bulge_w", 1)
        waist = p.get("waist_w", 1)
        depth = max(0.5, (bulge - waist) / 2.0)
        return min(0.40, depth / max(bulge, 1) * 0.8)


# 12. Ribbon plate (notched-end rectangle)
class SimpleFilletedRibbonPlateFamily(_FilletedPolyFamily):
    name = "simple_filleted_ribbon_plate"
    REF = "imagined: die-cut ribbon banner with notched ends + rounded corners"

    def _sample_size(self, difficulty, rng):
        L = round(float(rng.uniform(70, 130)), 1)
        W = round(L * float(rng.uniform(0.18, 0.35)), 1)
        return {
            "length": L,
            "width": W,
            "notch_d": round(W * float(rng.uniform(0.4, 0.8)), 1),
            "thickness": round(float(rng.uniform(2, 7)), 1),
        }

    def _make_pts(self, p):
        return _ribbon_pts(p["length"], p["width"], p["notch_d"])

    def _max_fillet_factor(self, p):
        return 0.30


ALL_FAMILIES = [
    SimpleFilletedLPlateFamily,
    SimpleFilletedTPlateFamily,
    SimpleFilletedUPlateFamily,
    SimpleFilletedCrossPlateFamily,
    SimpleFilletedStepPlateFamily,
    SimpleFilletedZigzagPlateFamily,
    SimpleFilletedHexagonPlateFamily,
    SimpleFilletedOctagonPlateFamily,
    SimpleFilletedArrowPlateFamily,
    SimpleFilletedChevronPlateFamily,
    SimpleFilletedDumbbellPlateFamily,
    SimpleFilletedRibbonPlateFamily,
]
