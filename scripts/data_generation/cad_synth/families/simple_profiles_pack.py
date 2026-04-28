"""simple_profiles_pack — 30 sketch-first 2D-extrude families.

Reference: derived from F360 reconstruction r1.0.1 sample shapes (138 samples
visually classified — see PROGRESS.md UA-24). Each family represents one
2D-profile category that recurs in the dataset.

All families are薄板 sketch-first style: build a closed polyline (or circle)
profile in the XY plane, then a single .extrude(). Variants control profile
parameters but keep the op chain identical.

Common pattern:
  moveTo(p0) → lineTo(p1) → ... → close → extrude(thickness)
  optional: + bore / + chamfer / + fillet edges

Family list & ref samples (Fusion360 stems shown):
  simple_trapezoid_plate      (ref: 102416_eba35f73_0005_0114e style)
  simple_parallelogram_plate  (ref: 23258_87a2ba81_0004_0057e)
  simple_wedge_block          (ref: 139863_77335f61_0000_0001e)
  simple_rounded_rect_plate   (general fillet + extrude pattern)
  simple_capsule_plate        (slot2D-style stadium)
  simple_half_disc_plate      (ref: F360 page-5 capsules)
  simple_pie_slice_plate      (ref: 56045_d9d572d5 wedge chunks)
  simple_diamond_plate        (ref: F360 page-2 red rhombi)
  simple_chevron_plate        (V-shape arrow)
  simple_pentagon_block       (5-side polygon prism)
  simple_hexagon_block        (ref: 128043_0017e0c6_0000_0001e)
  simple_heptagon_block       (7-side, less common)
  simple_octagon_block        (8-side polygon prism, common nuts)
  simple_n_star_plate         (parametric N-point star outline)
  simple_cross_plate          (ref: 43628_a95b7e66_0036_0479e plus shape)
  simple_arrow_plate          (single-direction arrow)
  simple_house_plate          (square + triangle pediment)
  simple_keyhole_plate        (round + rect tail; bracketing key insertion)
  simple_stadium_plate        (rect with semi-circular ends)
  simple_slot_through_plate   (rect plate + 1 thru rect slot)
  simple_d_shape_plate        (cylinder with one flat — D-shaped cross)
  simple_quarter_disc_plate   (90° pie slice)
  simple_annulus_plate        (concentric ring single-extrude)
  simple_crescent_plate       (ref: F360 page-3 crescents)
  simple_dogbone_plate        (rect + 2 round end-bosses on opposite sides)
  simple_h_section_plate      (H-cross-section i-beam-style)
  simple_z_section_plate      (Z-fold sheet metal: ref 56430_4f35ba2f zigzag)
  simple_y_shape_plate        (3-arm symmetric Y)
  simple_corrugated_sheet     (ref: 23743_a0373929_0000_0014e washboard)
  simple_serrated_plate       (sawtooth edge along one side)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- helper polylines -----------------------------------------------


def _trapezoid(top_w, bot_w, h):
    return [(-bot_w / 2, 0), (bot_w / 2, 0), (top_w / 2, h), (-top_w / 2, h)]


def _parallelogram(w, h, skew):
    return [(0, 0), (w, 0), (w + skew, h), (skew, h)]


def _wedge(base_w, h, peak_x):
    return [(0, 0), (base_w, 0), (peak_x, h)]


def _diamond(w, h):
    return [(0, h / 2), (w / 2, 0), (w, h / 2), (w / 2, h)]


def _chevron(w, h, t):
    """V-arrow with thickness t."""
    return [
        (0, 0),
        (w / 2, h),
        (w, 0),
        (w - t, 0),
        (w / 2, h - t * 1.5),
        (t, 0),
    ]


def _cross(w, t):
    """Plus shape with arm width t and total span w."""
    return [
        (-t / 2, -w / 2),
        (t / 2, -w / 2),
        (t / 2, -t / 2),
        (w / 2, -t / 2),
        (w / 2, t / 2),
        (t / 2, t / 2),
        (t / 2, w / 2),
        (-t / 2, w / 2),
        (-t / 2, t / 2),
        (-w / 2, t / 2),
        (-w / 2, -t / 2),
        (-t / 2, -t / 2),
    ]


def _arrow(w, h, head_w, head_h, shaft_w):
    """Single-direction arrow pointing +X. Origin is tail center."""
    return [
        (0, -shaft_w / 2),
        (w - head_h, -shaft_w / 2),
        (w - head_h, -head_w / 2),
        (w, 0),
        (w - head_h, head_w / 2),
        (w - head_h, shaft_w / 2),
        (0, shaft_w / 2),
    ]


def _house(w, h, roof_h):
    return [
        (0, 0),
        (w, 0),
        (w, h),
        (w / 2, h + roof_h),
        (0, h),
    ]


def _keyhole(circ_r, slot_w, slot_h):
    """Big circle on top, narrow rect tail going down."""
    pts = []
    n_arc = 24
    # Half circle from far-right of circle going CCW around top to far-left
    for i in range(n_arc + 1):
        a = -math.pi / 2 + i * (2 * math.pi - math.pi) / n_arc
        # Actually we want full circle minus the narrow slot opening
        # Simpler: full circle minus chord cut by slot. Use parametric:
        pass
    # Instead just emit tear-drop polyline approximation
    pts = []
    for i in range(36):
        a = math.pi / 2 + i * 2 * math.pi / 36
        pts.append((round(circ_r * math.cos(a), 3), round(circ_r * math.sin(a), 3)))
    # Replace bottom 6 pts with slot
    bot_idx = list(range(15, 22))  # bottom of circle
    new_pts = []
    inserted = False
    for i, p in enumerate(pts):
        if i in bot_idx:
            if not inserted:
                new_pts.append((slot_w / 2, 0))
                new_pts.append((slot_w / 2, -slot_h))
                new_pts.append((-slot_w / 2, -slot_h))
                new_pts.append((-slot_w / 2, 0))
                inserted = True
            continue
        new_pts.append(p)
    return new_pts


def _stadium(L, W, n_arc=12):
    """Stadium / discorectangle: rect of length L+2r, width 2r where r = W/2."""
    r = W / 2
    flat_x = L / 2
    pts = []
    # Right semicircle (top of rect → bottom)
    for i in range(n_arc + 1):
        a = math.pi / 2 - i * math.pi / n_arc
        pts.append((flat_x + r * math.cos(a), r * math.sin(a)))
    # Left semicircle
    for i in range(n_arc + 1):
        a = -math.pi / 2 - i * math.pi / n_arc
        pts.append((-flat_x + r * math.cos(a), r * math.sin(a)))
    return pts


def _half_disc(r, n_arc=24):
    pts = [(-r, 0), (r, 0)]
    for i in range(1, n_arc):
        a = i * math.pi / n_arc
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def _pie_slice(r, sweep_deg, n_arc=24):
    pts = [(0, 0), (r, 0)]
    sweep = math.radians(sweep_deg)
    for i in range(1, n_arc + 1):
        a = i * sweep / n_arc
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def _quarter_disc(r, n_arc=18):
    return _pie_slice(r, 90, n_arc)


def _star(n_pts, r_out, r_in, rot_deg=0):
    pts = []
    base = math.radians(rot_deg) + math.pi / 2
    for i in range(2 * n_pts):
        a = base + i * math.pi / n_pts
        rr = r_out if i % 2 == 0 else r_in
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return pts


def _crescent(r_outer, r_inner, offset, n_arc=24):
    """Crescent: outer arc 180° then inner arc 180° offset."""
    pts = []
    for i in range(n_arc + 1):
        a = i * math.pi / n_arc
        pts.append((r_outer * math.cos(a), r_outer * math.sin(a)))
    for i in range(n_arc + 1):
        a = math.pi - i * math.pi / n_arc
        pts.append((offset + r_inner * math.cos(a), r_inner * math.sin(a)))
    return pts


def _dogbone(L, W, end_r):
    """Rect + circle bosses at both ends going +Y/-Y."""
    pts = []
    pts.append((-L / 2, -W / 2))
    pts.append((L / 2 - end_r, -W / 2))
    # right boss arc
    for i in range(13):
        a = -math.pi / 2 + i * math.pi / 12
        pts.append((L / 2 - end_r + end_r * math.cos(a), -W / 2 + end_r * math.sin(a)))
    pts.append((L / 2 - end_r, W / 2))
    pts.append((-L / 2 + end_r, W / 2))
    for i in range(13):
        a = math.pi / 2 + i * math.pi / 12
        pts.append((-L / 2 + end_r + end_r * math.cos(a), W / 2 + end_r * math.sin(a)))
    return pts


def _h_section(W, H, t_flange, t_web):
    """H-beam cross section."""
    fl = t_flange
    return [
        (-W / 2, -H / 2),
        (W / 2, -H / 2),
        (W / 2, -H / 2 + fl),
        (t_web / 2, -H / 2 + fl),
        (t_web / 2, H / 2 - fl),
        (W / 2, H / 2 - fl),
        (W / 2, H / 2),
        (-W / 2, H / 2),
        (-W / 2, H / 2 - fl),
        (-t_web / 2, H / 2 - fl),
        (-t_web / 2, -H / 2 + fl),
        (-W / 2, -H / 2 + fl),
    ]


def _z_section(W, H, t):
    """Z-fold sheet metal cross section."""
    return [
        (0, 0),
        (W, 0),
        (W, t),
        (t, t),
        (t, H - t),
        (W, H - t),
        (W, H),
        (0, H),
        (
            0,
            t,
        ),  # close; this becomes the back-face hole — but the polyline is a flat outline
    ]


def _y_shape(arm_l, arm_w, n_arms=3):
    """N-arm Y-shape outline. Each arm is a rectangular strip joined at center."""
    pts = []
    for i in range(n_arms):
        # angle of this arm centerline
        a = i * 2 * math.pi / n_arms - math.pi / 2
        # next arm angle
        a_next = ((i + 1) % n_arms) * 2 * math.pi / n_arms - math.pi / 2
        c, s = math.cos(a), math.sin(a)
        # perpendicular unit
        px, py = -s, c
        tip_l = (arm_l * c + px * arm_w / 2, arm_l * s + py * arm_w / 2)
        tip_r = (arm_l * c - px * arm_w / 2, arm_l * s - py * arm_w / 2)
        pts.append(tip_l)
        pts.append(tip_r)
        # half-angle to next arm
        c2, s2 = math.cos(a_next), math.sin(a_next)
        _px2, _py2 = -s2, c2
        # corner near root between this arm's right edge and next arm's left edge
        inner_r = arm_w * 0.6
        bisect_a = (a + a_next) / 2
        pts.append((inner_r * math.cos(bisect_a), inner_r * math.sin(bisect_a)))
    return pts


def _corrugated(L, n_corr, amp, base_h):
    """Top edge has sinusoidal-ish corrugation; bottom flat."""
    pts = [(0, 0)]
    n_pts = max(40, n_corr * 6)
    for i in range(n_pts + 1):
        x = L * i / n_pts
        y = base_h + amp * math.sin(2 * math.pi * n_corr * i / n_pts)
        pts.append((x, y))
    pts.append((L, 0))
    return pts


def _serrated(L, n_teeth, base_h, tooth_h):
    """Sawtooth edge on top. Uses unique points to avoid coincident-vertex BRep failures."""
    pts = [(0, 0), (0, base_h)]
    for i in range(n_teeth):
        x_l = L * i / n_teeth
        x_r = L * (i + 1) / n_teeth
        x_m = (x_l + x_r) / 2
        # tooth: rise from (x_l, base_h) → (x_m, base_h + tooth_h) → fall to (x_r, base_h)
        # Skip (x_l, base_h) for i>0 since it equals previous (x_r, base_h)
        if i == 0:
            pts.append((x_m, base_h + tooth_h))
        else:
            pts.append((x_m, base_h + tooth_h))
        pts.append((x_r, base_h))
    pts.append((L, 0))
    return pts


def _polygon_pts(n, r):
    return [
        (
            r * math.cos(2 * math.pi * i / n + math.pi / 2),
            r * math.sin(2 * math.pi * i / n + math.pi / 2),
        )
        for i in range(n)
    ]


def _polygon_program(self, p, n_sides, ref_note):
    pts = _polygon_pts(n_sides, p["radius"])
    pts = [(round(x, 3), round(y, 3)) for x, y in pts]
    ops = [Op("moveTo", {"x": pts[0][0], "y": pts[0][1]})]
    for x, y in pts[1:]:
        ops.append(Op("lineTo", {"x": x, "y": y}))
    ops += [Op("close", {}), Op("extrude", {"distance": p["thickness"]})]
    if p.get("with_bore"):
        ops += [
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["bore_d"]}),
        ]
    return Program(
        family=self.name,
        difficulty=p["difficulty"],
        params=p,
        ops=ops,
        feature_tags={"n_sides": n_sides, "ref": ref_note},
    )


# ---------- generic emitter ------------------------------------------------


def _emit_poly_extrude(
    name, pts, thickness, with_bore=False, bore_d=0, chamfer=None, fillet=None
):
    """Emit ops for: moveTo + polyline + close + extrude + optional features."""
    pts_r = [(round(x, 3), round(y, 3)) for x, y in pts]
    ops = [Op("moveTo", {"x": pts_r[0][0], "y": pts_r[0][1]})]
    for x, y in pts_r[1:]:
        ops.append(Op("lineTo", {"x": x, "y": y}))
    ops += [Op("close", {}), Op("extrude", {"distance": thickness})]
    if with_bore and bore_d > 0:
        ops += [Op("workplane", {"selector": ">Z"}), Op("hole", {"diameter": bore_d})]
    if chamfer:
        ops += [Op("edges", {"selector": ">Z"}), Op("chamfer", {"length": chamfer})]
    if fillet:
        ops += [Op("edges", {"selector": "|Z"}), Op("fillet", {"radius": fillet})]
    return ops


# ---------- families -------------------------------------------------------


class _PolyFamily(BaseFamily):
    """Base for sketch-first poly + extrude families. Subclasses override _make_pts + _sample_size."""

    standard = "N/A"
    REF = ""

    def _sample_size(self, difficulty, rng):
        return {"thickness": round(float(rng.uniform(3, 12)), 1)}

    def _make_pts(self, p, rng):
        raise NotImplementedError

    # Default: skip chamfer/fillet on polyline outlines — BRep often fails on
    # complex polylines. Subclasses with simple convex outlines may opt-in by
    # setting ALLOW_FEATURES = True.
    ALLOW_FEATURES = False

    def sample_params(self, difficulty, rng):
        p = {"difficulty": difficulty}
        p.update(self._sample_size(difficulty, rng))
        if difficulty == "hard" and self.ALLOW_FEATURES:
            if rng.uniform(0, 1) < 0.4:
                p["chamfer"] = round(
                    float(rng.uniform(0.3, min(1.5, p.get("thickness", 5) * 0.3))), 2
                )
            if rng.uniform(0, 1) < 0.3:
                p["fillet"] = round(float(rng.uniform(0.5, 2.0)), 2)
        return p

    def validate_params(self, p):
        return p.get("thickness", 0) >= 1.5

    def make_program(self, p):
        rng = None  # not needed since we re-derive from p
        try:
            pts = self._make_pts(p, rng)
        except Exception as e:
            raise ValueError(f"{self.name} pts gen failed: {e}") from e
        ops = _emit_poly_extrude(
            self.name,
            pts,
            p["thickness"],
            chamfer=p.get("chamfer"),
            fillet=p.get("fillet"),
        )
        tags = {"thin_plate": True, "ref": self.REF}
        if p.get("chamfer"):
            tags["has_chamfer"] = True
        if p.get("fillet"):
            tags["has_fillet"] = True
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )


# 1. simple_trapezoid_plate
class SimpleTrapezoidPlateFamily(_PolyFamily):
    name = "simple_trapezoid_plate"
    REF = "f360:102416_eba35f73"

    def _sample_size(self, difficulty, rng):
        bot = round(float(rng.uniform(40, 90)), 1)
        return {
            "top_w": round(bot * float(rng.uniform(0.4, 0.85)), 1),
            "bot_w": bot,
            "height": round(float(rng.uniform(20, 60)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _trapezoid(p["top_w"], p["bot_w"], p["height"])


# 2. simple_parallelogram_plate
class SimpleParallelogramPlateFamily(_PolyFamily):
    name = "simple_parallelogram_plate"
    REF = "f360:23258_87a2ba81"

    def _sample_size(self, difficulty, rng):
        return {
            "width": round(float(rng.uniform(40, 90)), 1),
            "height": round(float(rng.uniform(20, 50)), 1),
            "skew": round(float(rng.uniform(8, 25)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _parallelogram(p["width"], p["height"], p["skew"])


# 3. simple_wedge_block
class SimpleWedgeBlockFamily(_PolyFamily):
    name = "simple_wedge_block"
    REF = "f360:139863_77335f61"

    def _sample_size(self, difficulty, rng):
        bw = round(float(rng.uniform(30, 80)), 1)
        return {
            "base_w": bw,
            "height": round(float(rng.uniform(20, 50)), 1),
            "peak_x": round(bw * float(rng.uniform(0.3, 0.7)), 1),
            "thickness": round(float(rng.uniform(8, 20)), 1),
        }

    def _make_pts(self, p, rng):
        return _wedge(p["base_w"], p["height"], p["peak_x"])


# 4. simple_diamond_plate
class SimpleDiamondPlateFamily(_PolyFamily):
    name = "simple_diamond_plate"
    REF = "f360:page2_red_rhombi"

    def _sample_size(self, difficulty, rng):
        return {
            "width": round(float(rng.uniform(40, 90)), 1),
            "height": round(float(rng.uniform(40, 90)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p, rng):
        return _diamond(p["width"], p["height"])


# 5. simple_chevron_plate
class SimpleChevronPlateFamily(_PolyFamily):
    name = "simple_chevron_plate"
    REF = "imagined: V-arrow road sign style"

    def _sample_size(self, difficulty, rng):
        w = round(float(rng.uniform(40, 90)), 1)
        return {
            "width": w,
            "height": round(w * float(rng.uniform(0.5, 0.9)), 1),
            "arm_thickness": round(w * float(rng.uniform(0.12, 0.25)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p, rng):
        return _chevron(p["width"], p["height"], p["arm_thickness"])


# 6. simple_cross_plate
class SimpleCrossPlateFamily(_PolyFamily):
    name = "simple_cross_plate"
    REF = "f360:43628_a95b7e66 plus shape"

    def _sample_size(self, difficulty, rng):
        w = round(float(rng.uniform(40, 90)), 1)
        return {
            "span": w,
            "arm_t": round(w * float(rng.uniform(0.2, 0.4)), 1),
            "thickness": round(float(rng.uniform(4, 12)), 1),
        }

    def _make_pts(self, p, rng):
        return _cross(p["span"], p["arm_t"])


# 7. simple_arrow_plate
class SimpleArrowPlateFamily(_PolyFamily):
    name = "simple_arrow_plate"
    REF = "imagined: directional arrow signage"

    def _sample_size(self, difficulty, rng):
        w = round(float(rng.uniform(60, 120)), 1)
        return {
            "length": w,
            "head_h": round(w * float(rng.uniform(0.25, 0.4)), 1),
            "head_w": round(w * float(rng.uniform(0.4, 0.7)), 1),
            "shaft_w": round(w * float(rng.uniform(0.15, 0.3)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p, rng):
        return _arrow(p["length"], 0, p["head_w"], p["head_h"], p["shaft_w"])


# 8. simple_house_plate
class SimpleHousePlateFamily(_PolyFamily):
    name = "simple_house_plate"
    REF = "imagined: pediment-house silhouette"

    def _sample_size(self, difficulty, rng):
        w = round(float(rng.uniform(40, 90)), 1)
        return {
            "width": w,
            "height": round(w * float(rng.uniform(0.6, 1.1)), 1),
            "roof_h": round(w * float(rng.uniform(0.25, 0.5)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p, rng):
        return _house(p["width"], p["height"], p["roof_h"])


# 9. simple_pentagon_block
class SimplePentagonBlockFamily(_PolyFamily):
    name = "simple_pentagon_block"
    REF = "f360:128043 polygon prism style"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 35)), 1),
            "thickness": round(float(rng.uniform(8, 25)), 1),
        }

    def _make_pts(self, p, rng):
        return _polygon_pts(5, p["radius"])


# 10. simple_hexagon_block
class SimpleHexagonBlockFamily(_PolyFamily):
    name = "simple_hexagon_block"
    REF = "f360:128043_0017e0c6 hex prism"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 40)), 1),
            "thickness": round(float(rng.uniform(8, 30)), 1),
        }

    def _make_pts(self, p, rng):
        return _polygon_pts(6, p["radius"])


# 11. simple_heptagon_block
class SimpleHeptagonBlockFamily(_PolyFamily):
    name = "simple_heptagon_block"
    REF = "imagined: 7-sided polygon prism"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 35)), 1),
            "thickness": round(float(rng.uniform(8, 25)), 1),
        }

    def _make_pts(self, p, rng):
        return _polygon_pts(7, p["radius"])


# 12. simple_octagon_block
class SimpleOctagonBlockFamily(_PolyFamily):
    name = "simple_octagon_block"
    REF = "imagined: 8-sided nut/bolt cross-section"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 40)), 1),
            "thickness": round(float(rng.uniform(8, 30)), 1),
        }

    def _make_pts(self, p, rng):
        return _polygon_pts(8, p["radius"])


# 13. simple_n_star_plate (parametric N-pointed star)
class SimpleNStarPlateFamily(_PolyFamily):
    name = "simple_n_star_plate"
    REF = "imagined: 5/6/8-point star (signage, decoration)"
    ALLOW_FEATURES = False  # star points break chamfer/fillet

    def _sample_size(self, difficulty, rng):
        n = int(rng.choice([5, 6, 7, 8]))
        ro = round(float(rng.uniform(20, 40)), 1)
        return {
            "n_points": n,
            "r_out": ro,
            "r_in": round(ro * float(rng.uniform(0.4, 0.6)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _star(p["n_points"], p["r_out"], p["r_in"])


# 14. simple_keyhole_plate
class SimpleKeyholePlateFamily(_PolyFamily):
    name = "simple_keyhole_plate"
    REF = "imagined: door keyhole escutcheon"

    def _sample_size(self, difficulty, rng):
        return {
            "circ_r": round(float(rng.uniform(10, 22)), 1),
            "slot_w": round(float(rng.uniform(2, 5)), 1),
            "slot_h": round(float(rng.uniform(15, 35)), 1),
            "thickness": round(float(rng.uniform(2, 6)), 1),
        }

    def _make_pts(self, p, rng):
        return _keyhole(p["circ_r"], p["slot_w"], p["slot_h"])


# 15. simple_stadium_plate
class SimpleStadiumPlateFamily(_PolyFamily):
    name = "simple_stadium_plate"
    REF = "imagined: stadium/track 2D outline"

    def _sample_size(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(40, 90)), 1),
            "width": round(float(rng.uniform(15, 35)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _stadium(p["length"], p["width"])


# 16. simple_half_disc_plate
class SimpleHalfDiscPlateFamily(_PolyFamily):
    name = "simple_half_disc_plate"
    REF = "f360:page-5 capsule halves"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(15, 40)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _half_disc(p["radius"])


# 17. simple_pie_slice_plate
class SimplePieSlicePlateFamily(_PolyFamily):
    name = "simple_pie_slice_plate"
    REF = "f360:56045_d9d572d5 pie wedge"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(20, 45)), 1),
            "sweep_deg": float(rng.choice([45, 60, 90, 120, 135, 150])),
            "thickness": round(float(rng.uniform(4, 12)), 1),
        }

    def _make_pts(self, p, rng):
        return _pie_slice(p["radius"], p["sweep_deg"])


# 18. simple_quarter_disc_plate
class SimpleQuarterDiscPlateFamily(_PolyFamily):
    name = "simple_quarter_disc_plate"
    REF = "imagined: 90° fillet-corner brace"

    def _sample_size(self, difficulty, rng):
        return {
            "radius": round(float(rng.uniform(20, 45)), 1),
            "thickness": round(float(rng.uniform(4, 12)), 1),
        }

    def _make_pts(self, p, rng):
        return _quarter_disc(p["radius"])


# 19. simple_crescent_plate
class SimpleCrescentPlateFamily(_PolyFamily):
    name = "simple_crescent_plate"
    REF = "f360:page-3 crescent arcs"

    def _sample_size(self, difficulty, rng):
        ro = round(float(rng.uniform(20, 40)), 1)
        return {
            "r_outer": ro,
            "r_inner": round(ro * float(rng.uniform(0.5, 0.85)), 1),
            "offset": round(ro * float(rng.uniform(0.15, 0.35)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p, rng):
        return _crescent(p["r_outer"], p["r_inner"], p["offset"])


# 20. simple_dogbone_plate
class SimpleDogbonePlateFamily(_PolyFamily):
    name = "simple_dogbone_plate"
    REF = "imagined: tensile-test specimen / dog bone link"

    def _sample_size(self, difficulty, rng):
        L = round(float(rng.uniform(50, 100)), 1)
        return {
            "length": L,
            "width": round(L * float(rng.uniform(0.18, 0.32)), 1),
            "end_r": round(L * float(rng.uniform(0.12, 0.2)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _dogbone(p["length"], p["width"], p["end_r"])


# 21. simple_h_section_plate
class SimpleHSectionPlateFamily(_PolyFamily):
    name = "simple_h_section_plate"
    REF = "imagined: I-beam cross-section sliced thin"

    def _sample_size(self, difficulty, rng):
        return {
            "width": round(float(rng.uniform(40, 80)), 1),
            "height": round(float(rng.uniform(40, 80)), 1),
            "t_flange": round(float(rng.uniform(4, 10)), 1),
            "t_web": round(float(rng.uniform(3, 8)), 1),
            "thickness": round(float(rng.uniform(15, 40)), 1),
        }

    def _make_pts(self, p, rng):
        return _h_section(p["width"], p["height"], p["t_flange"], p["t_web"])


# 22. simple_z_section_plate
class SimpleZSectionPlateFamily(_PolyFamily):
    name = "simple_z_section_plate"
    REF = "f360:56430_4f35ba2f Z-fold sheet"

    def _sample_size(self, difficulty, rng):
        return {
            "width": round(float(rng.uniform(40, 80)), 1),
            "height": round(float(rng.uniform(40, 80)), 1),
            "thickness_2d": round(float(rng.uniform(4, 10)), 1),
            "thickness": round(float(rng.uniform(8, 25)), 1),
        }

    def _make_pts(self, p, rng):
        return _z_section(p["width"], p["height"], p["thickness_2d"])


# 23. simple_y_shape_plate
class SimpleYShapePlateFamily(_PolyFamily):
    name = "simple_y_shape_plate"
    REF = "imagined: 3-arm symmetric yoke / Mercedes-style"

    def _sample_size(self, difficulty, rng):
        return {
            "arm_l": round(float(rng.uniform(25, 50)), 1),
            "arm_w": round(float(rng.uniform(10, 22)), 1),
            "thickness": round(float(rng.uniform(4, 10)), 1),
        }

    def _make_pts(self, p, rng):
        return _y_shape(p["arm_l"], p["arm_w"])


# 24. simple_corrugated_sheet
class SimpleCorrugatedSheetFamily(_PolyFamily):
    name = "simple_corrugated_sheet"
    REF = "f360:23743_a0373929 washboard ribs"

    def _sample_size(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(60, 120)), 1),
            "n_corr": int(rng.choice([4, 6, 8, 10, 12])),
            "amplitude": round(float(rng.uniform(2, 6)), 1),
            "base_h": round(float(rng.uniform(8, 18)), 1),
            "thickness": round(float(rng.uniform(8, 25)), 1),
        }

    def _make_pts(self, p, rng):
        return _corrugated(p["length"], p["n_corr"], p["amplitude"], p["base_h"])


# 25. simple_serrated_plate
class SimpleSerratedPlateFamily(_PolyFamily):
    name = "simple_serrated_plate"
    REF = "imagined: saw blade / guard"

    def _sample_size(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(50, 110)), 1),
            "n_teeth": int(rng.choice([6, 8, 10, 12, 16])),
            "base_h": round(float(rng.uniform(15, 35)), 1),
            "tooth_h": round(float(rng.uniform(3, 8)), 1),
            "thickness": round(float(rng.uniform(3, 8)), 1),
        }

    def _make_pts(self, p, rng):
        return _serrated(p["length"], p["n_teeth"], p["base_h"], p["tooth_h"])


# 26. simple_d_shape_plate (cylinder with a flat — D shape)
class SimpleDShapePlateFamily(_PolyFamily):
    name = "simple_d_shape_plate"
    REF = "imagined: D-shaped shaft cross-section"

    def _sample_size(self, difficulty, rng):
        r = round(float(rng.uniform(15, 35)), 1)
        return {
            "radius": r,
            "flat_offset": round(r * float(rng.uniform(0.2, 0.6)), 1),
            "thickness": round(float(rng.uniform(4, 14)), 1),
        }

    def _make_pts(self, p, rng):
        r = p["radius"]
        flat_y = -p["flat_offset"]
        # arc from (-x, flat_y) on circle to (+x, flat_y) on circle
        x_at_flat = math.sqrt(max(0.001, r * r - flat_y * flat_y))
        pts = [(x_at_flat, flat_y), (-x_at_flat, flat_y)]
        # CCW arc going through top
        math.pi - math.atan2(flat_y, -x_at_flat)
        # easier: parametric over arc
        n = 32
        for i in range(1, n):
            ang = (
                math.atan2(flat_y, -x_at_flat)
                + i
                * (
                    math.atan2(flat_y, x_at_flat)
                    + 2 * math.pi
                    - math.atan2(flat_y, -x_at_flat)
                )
                / n
            )
            pts.append((r * math.cos(ang), r * math.sin(ang)))
        return pts


# 27. simple_annulus_plate (ring single extrude)
class SimpleAnnulusPlateFamily(BaseFamily):
    name = "simple_annulus_plate"
    standard = "N/A"
    REF = "imagined: flat washer / spacer ring"

    def sample_params(self, difficulty, rng):
        ro = round(float(rng.uniform(15, 40)), 1)
        return {
            "r_outer": ro,
            "r_inner": round(ro * float(rng.uniform(0.4, 0.8)), 1),
            "thickness": round(float(rng.uniform(2, 8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["r_outer"] > p["r_inner"] + 1 and p["thickness"] >= 1.5

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_outer"]}),
            Op("circle", {"radius": p["r_inner"]}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "ref": self.REF},
        )


# 28. simple_rounded_rect_plate
class SimpleRoundedRectPlateFamily(BaseFamily):
    name = "simple_rounded_rect_plate"
    standard = "N/A"
    REF = "imagined: rounded-corner sheet metal blank"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(50, 100)), 1),
            "width": round(float(rng.uniform(30, 70)), 1),
            "fillet_r": round(float(rng.uniform(3, 12)), 1),
            "thickness": round(float(rng.uniform(2, 8)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] > 2 * p["fillet_r"] + 4
            and p["width"] > 2 * p["fillet_r"] + 4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        ops = [
            Op("rect", {"length": p["length"], "width": p["width"]}),
            Op("extrude", {"distance": p["thickness"]}),
            Op("edges", {"selector": "|Z"}),
            Op("fillet", {"radius": p["fillet_r"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "has_fillet": True, "ref": self.REF},
        )


# 29. simple_capsule_plate (uses slot2D primitive)
class SimpleCapsulePlateFamily(BaseFamily):
    name = "simple_capsule_plate"
    standard = "N/A"
    REF = "imagined: capsule / slot blank"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(40, 90)), 1),
            "width": round(float(rng.uniform(15, 35)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["length"] > p["width"] + 4 and p["thickness"] >= 2

    def make_program(self, p):
        ops = [
            Op("slot2D", {"length": p["length"], "width": p["width"]}),
            Op("extrude", {"distance": p["thickness"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "ref": self.REF},
        )


# 30. simple_slot_through_plate (rect + thru rect slot cut)
class SimpleSlotThroughPlateFamily(BaseFamily):
    name = "simple_slot_through_plate"
    standard = "N/A"
    REF = "imagined: mounting plate w/ keyway slot"

    def sample_params(self, difficulty, rng):
        return {
            "length": round(float(rng.uniform(60, 110)), 1),
            "width": round(float(rng.uniform(30, 70)), 1),
            "thickness": round(float(rng.uniform(3, 10)), 1),
            "slot_l": round(float(rng.uniform(20, 50)), 1),
            "slot_w": round(float(rng.uniform(4, 10)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] > p["slot_l"] + 8
            and p["width"] > p["slot_w"] + 8
            and p["thickness"] >= 2
        )

    def make_program(self, p):
        ops = [
            Op("rect", {"length": p["length"], "width": p["width"]}),
            Op("extrude", {"distance": p["thickness"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("slot2D", {"length": p["slot_l"], "width": p["slot_w"]}),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "has_slot": True, "ref": self.REF},
        )


ALL_FAMILIES = [
    SimpleTrapezoidPlateFamily,
    SimpleParallelogramPlateFamily,
    SimpleWedgeBlockFamily,
    SimpleDiamondPlateFamily,
    SimpleChevronPlateFamily,
    SimpleCrossPlateFamily,
    SimpleArrowPlateFamily,
    SimpleHousePlateFamily,
    SimplePentagonBlockFamily,
    SimpleHexagonBlockFamily,
    SimpleHeptagonBlockFamily,
    SimpleOctagonBlockFamily,
    SimpleNStarPlateFamily,
    SimpleKeyholePlateFamily,
    SimpleStadiumPlateFamily,
    SimpleHalfDiscPlateFamily,
    SimplePieSlicePlateFamily,
    SimpleQuarterDiscPlateFamily,
    SimpleCrescentPlateFamily,
    SimpleDogbonePlateFamily,
    SimpleHSectionPlateFamily,
    SimpleZSectionPlateFamily,
    SimpleYShapePlateFamily,
    SimpleCorrugatedSheetFamily,
    SimpleSerratedPlateFamily,
    SimpleDShapePlateFamily,
    SimpleAnnulusPlateFamily,
    SimpleRoundedRectPlateFamily,
    SimpleCapsulePlateFamily,
    SimpleSlotThroughPlateFamily,
]
