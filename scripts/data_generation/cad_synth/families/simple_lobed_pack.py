"""simple_lobed_pack — closed symmetric symbol outlines.

Topology class: closed 2D outline with rotational/reflection symmetry around a
center point. Built as a single closed polyline (or union of components for
multi-component shapes), then a single extrude. No internal cuts (distinct
from face_pack), not single-stroke open (distinct from alphabet).

Family list:
  simple_clover_3leaf_plate     3-leaf clover (shamrock)
  simple_clover_4leaf_plate     4-leaf clover
  simple_flower_5petal_plate    5-petal flower outline
  simple_flower_8petal_plate    8-petal rounded flower
  simple_butterfly_plate        butterfly silhouette (4 wings)
  simple_diamond_lobed_plate    diamond with 4 outward-bulging arcs
  simple_gear_outline_plate     gear-like silhouette (no center hole)
  simple_fan_blade_plate        single fan blade (asym crescent + tail)
  simple_paw_print_plate        main pad + 4 toe pads (union)
  simple_anchor_plate           shaft + ring + 2 sym hooks (union)

Reference style: imagined (no F360 source — all parametrically authored).
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- shared helpers --------------------------------------------------


def _r3(x):
    return round(float(x), 3)


def _round_pts(pts):
    return [(_r3(p[0]), _r3(p[1])) for p in pts]


def _emit_polyline_extrude(pts, thickness):
    """Emit a closed polyline + single extrude."""
    return [
        Op("polyline", {"points": _round_pts(pts)}),
        Op("close", {}),
        Op("extrude", {"distance": _r3(thickness)}),
    ]


def _circle_pts(cx, cy, r, n=40, a0=0.0, a1=2 * math.pi):
    """Sample arc from a0 to a1 (CCW), n points (excludes endpoint to chain)."""
    out = []
    for i in range(n):
        t = a0 + (a1 - a0) * i / n
        out.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return out


def _full_circle_pts(cx, cy, r, n=48):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        out.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return out


def _lobed_outline(n_lobes, r_inner, lobe_radius, n_per_lobe=24, phase=0.0):
    """N lobes evenly spaced. Each lobe is a circle of radius lobe_radius
    centered at angle k*2π/N at distance d from origin where d ensures the
    lobe arcs meet smoothly at the inner valley.

    The valley is at radius r_inner. The lobe centers sit at distance
    d = sqrt(r_inner^2 + lobe_radius^2) so that the lobe circle is tangent
    to a circle of radius r_inner at the valley point.

    Outline = for each lobe, sweep around the OUTER portion of its circle
    (the portion not occluded by neighbors), connecting smoothly through the
    valley points.
    """
    # Half-angle subtended by each lobe at origin
    sector = 2 * math.pi / n_lobes
    # Distance from origin to lobe center: place lobe so it pokes out beyond r_inner.
    d = r_inner + 0.55 * lobe_radius  # heuristic: lobe slightly overlaps neighbor
    pts = []
    for k in range(n_lobes):
        theta_c = phase + k * sector  # angle of this lobe's center
        cx = d * math.cos(theta_c)
        cy = d * math.sin(theta_c)
        # Sweep this lobe from valley_in (left valley) to valley_out (right valley).
        # Lobe arc occupies angles around theta_c, from theta_c+sector/2 - π
        # going CCW through theta_c (outermost) to theta_c-sector/2 + π... but
        # simpler: sweep most of the circle, leaving a small chord at the back.
        # Use sweep from (theta_c - π + sector/2) to (theta_c + π - sector/2)
        # going CCW around the lobe.
        a0 = theta_c - math.pi + sector / 2
        a1 = theta_c + math.pi - sector / 2
        for j in range(n_per_lobe):
            t = a0 + (a1 - a0) * j / n_per_lobe
            pts.append((cx + lobe_radius * math.cos(t), cy + lobe_radius * math.sin(t)))
    return pts


# ---------- families --------------------------------------------------------


# 1. simple_clover_3leaf_plate
class SimpleClover3LeafPlateFamily(BaseFamily):
    name = "simple_clover_3leaf_plate"
    standard = "N/A"
    REF = "imagined: 3-leaf shamrock / triangular clover symbol"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(20, 40)), 1)
        lobe_ratio = float(rng.uniform(0.50, 0.70))
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "scale": scale,
            "lobe_ratio": lobe_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 15 and 0.4 <= p["lobe_ratio"] <= 0.8 and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        lr = s * p["lobe_ratio"]
        ri = s * 0.25  # small inner radius for valley
        pts = _lobed_outline(3, ri, lr, n_per_lobe=28, phase=math.pi / 2)
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "lobed": True,
                "n_lobes": 3,
                "ref": self.REF,
            },
        )


# 2. simple_clover_4leaf_plate
class SimpleClover4LeafPlateFamily(BaseFamily):
    name = "simple_clover_4leaf_plate"
    standard = "N/A"
    REF = "imagined: 4-leaf clover symbol"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(20, 40)), 1)
        lobe_ratio = float(rng.uniform(0.45, 0.65))
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "scale": scale,
            "lobe_ratio": lobe_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 15
            and 0.4 <= p["lobe_ratio"] <= 0.75
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        lr = s * p["lobe_ratio"]
        ri = s * 0.22
        pts = _lobed_outline(4, ri, lr, n_per_lobe=24, phase=math.pi / 4)
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "lobed": True,
                "n_lobes": 4,
                "ref": self.REF,
            },
        )


# 3. simple_flower_5petal_plate
class SimpleFlower5PetalPlateFamily(BaseFamily):
    name = "simple_flower_5petal_plate"
    standard = "N/A"
    REF = "imagined: 5-petal flower / daisy outline (top view)"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(22, 42)), 1)
        petal_ratio = float(rng.uniform(0.35, 0.55))
        thickness = round(float(rng.uniform(3, 9)), 1)
        return {
            "scale": scale,
            "petal_ratio": petal_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 15
            and 0.3 <= p["petal_ratio"] <= 0.6
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        lr = s * p["petal_ratio"]
        ri = s * 0.30  # bigger center for daisy
        pts = _lobed_outline(5, ri, lr, n_per_lobe=22, phase=math.pi / 2)
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "lobed": True,
                "n_lobes": 5,
                "ref": self.REF,
            },
        )


# 4. simple_flower_8petal_plate
class SimpleFlower8PetalPlateFamily(BaseFamily):
    name = "simple_flower_8petal_plate"
    standard = "N/A"
    REF = "imagined: 8-petal rounded flower (badge/medallion shape)"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(25, 45)), 1)
        petal_ratio = float(rng.uniform(0.25, 0.40))
        thickness = round(float(rng.uniform(3, 9)), 1)
        return {
            "scale": scale,
            "petal_ratio": petal_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 18
            and 0.2 <= p["petal_ratio"] <= 0.45
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        lr = s * p["petal_ratio"]
        ri = s * 0.40  # big center
        pts = _lobed_outline(8, ri, lr, n_per_lobe=18, phase=0.0)
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "lobed": True,
                "n_lobes": 8,
                "ref": self.REF,
            },
        )


# 5. simple_butterfly_plate
class SimpleButterflyPlateFamily(BaseFamily):
    name = "simple_butterfly_plate"
    standard = "N/A"
    REF = "imagined: butterfly silhouette (4 wings + body)"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(25, 45)), 1)
        body_ratio = float(rng.uniform(0.10, 0.18))
        upper_ratio = float(rng.uniform(0.55, 0.75))  # upper wing radius / scale
        lower_ratio = float(rng.uniform(0.40, 0.55))  # lower wing radius / scale
        thickness = round(float(rng.uniform(3, 9)), 1)
        return {
            "scale": scale,
            "body_ratio": body_ratio,
            "upper_ratio": upper_ratio,
            "lower_ratio": lower_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 18
            and 0.05 <= p["body_ratio"] <= 0.25
            and 0.4 <= p["upper_ratio"] <= 0.85
            and 0.3 <= p["lower_ratio"] <= 0.7
            and p["lower_ratio"] < p["upper_ratio"]
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        bw = s * p["body_ratio"]
        ru = s * p["upper_ratio"]
        rl = s * p["lower_ratio"]
        # 4 wings: upper-right, upper-left, lower-right, lower-left, plus a
        # central body (ellipse-ish via lobe). Build outline CCW starting at
        # the top of the body (above center), going right (upper-right wing),
        # down (lower-right wing), through bottom of body, then left (lower-
        # left wing), up (upper-left wing), back to top of body.
        # Body half-height
        bh = s * 0.45
        # Wing-circle centers
        cx_u = ru * 0.85  # upper-right wing center x
        cy_u = ru * 0.50  # upper-right wing center y (above x-axis)
        cx_l = rl * 0.85  # lower-right wing center x
        cy_l = -rl * 0.55  # lower-right wing center y
        # Wing-circle radii
        rcu = ru * 0.70
        rcl = rl * 0.70
        # Build path CCW.
        pts = []
        # Start at top of body
        pts.append((0.0, bh))
        # Sweep right around upper-right wing: arc from a top-inside point CCW
        # around the right side back to a bottom-inside meeting point on x-axis.
        # We approximate by sweeping the wing circle from angle ~110° down to
        # angle ~-80° (going CW from origin's perspective is CCW around the
        # outline).  Use 30 points per wing.
        n_w = 30

        def arc_pts(cx, cy, r, a0, a1, n):
            out = []
            for i in range(n + 1):
                t = a0 + (a1 - a0) * i / n
                out.append((cx + r * math.cos(t), cy + r * math.sin(t)))
            return out

        # Upper-right wing: sweep from inside-top (~135°) CCW around outer to
        # inside-bottom (~-135° = 225°). To go CCW around the OUTLINE we go CW
        # around the wing circle... easier: we go CCW along outline = around
        # the outer side of the wing circle from upper-inside to right-tip
        # to lower-inside.
        # From (0, bh) to upper-right wing top-inside corner: short straight.
        wing_ur_a0 = math.radians(150)  # upper-inside (toward body)
        wing_ur_a1 = math.radians(-60)  # lower-inside (toward body)
        # going CW (a0 → a1 with a1 < a0)
        pts += arc_pts(cx_u, cy_u, rcu, wing_ur_a0, wing_ur_a1, n_w)
        # Now between upper-right wing-end and lower-right wing-start, dip
        # toward body waist (small notch on +x side at y=0)
        pts.append((bw * 1.5, 0.0))
        # Lower-right wing: sweep CW from upper-inside (~60°) to lower-inside (~210°)
        wing_lr_a0 = math.radians(60)
        wing_lr_a1 = math.radians(-150)
        pts += arc_pts(cx_l, cy_l, rcl, wing_lr_a0, wing_lr_a1, n_w)
        # Bottom of body
        pts.append((0.0, -bh))
        # Lower-left wing (mirror of lower-right): sweep mirrored circle
        # from lower-inside up to upper-inside on the LEFT side.
        ll_a0 = math.radians(-180 + 150)  # = -30°
        ll_a1 = math.radians(-180 + -60)  # = -240° = 120° but we go CW
        pts += arc_pts(-cx_l, cy_l, rcl, ll_a0, ll_a1, n_w)
        # Inside-waist on -x side
        pts.append((-bw * 1.5, 0.0))
        # Upper-left wing (mirror of upper-right): we want CCW on left side
        # from lower-inside up to upper-inside = mirror of UR's CW.
        ul_a0_real = math.radians(60)  # upper-inside on left wing (mirror of 150°)
        ul_a1_real = math.radians(-120)  # lower-inside (mirror of -60°)
        # actually we want bottom→top so reverse:
        pts += arc_pts(-cx_u, cy_u, rcu, ul_a1_real, ul_a0_real, n_w)
        # close back to top of body
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "butterfly": True,
                "ref": self.REF,
            },
        )


# 6. simple_diamond_lobed_plate — diamond with 4 outward-bulging arcs
class SimpleDiamondLobedPlateFamily(BaseFamily):
    name = "simple_diamond_lobed_plate"
    standard = "N/A"
    REF = "imagined: diamond with 4 outward-bulging arcs (inflated rhombus)"

    def sample_params(self, difficulty, rng):
        size = round(float(rng.uniform(25, 50)), 1)
        bulge = float(rng.uniform(0.10, 0.25))  # how much arcs bulge outward
        aspect = float(rng.uniform(0.6, 1.0))  # height / width
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "size": size,
            "bulge": bulge,
            "aspect": aspect,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["size"] >= 15
            and 0.05 <= p["bulge"] <= 0.30
            and 0.5 <= p["aspect"] <= 1.2
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Diamond with vertices at (±W, 0) and (0, ±H). Each side is replaced
        # by an outward-bulging arc. We approximate each arc with N polyline
        # segments offset along the outward normal of each diamond edge.
        s = p["size"]
        W = s
        H = s * p["aspect"]
        bulge = p["bulge"] * s
        # Vertices, CCW from right tip
        verts = [(W, 0), (0, H), (-W, 0), (0, -H)]
        pts = []
        n_seg = 18  # per side
        for i in range(4):
            v0 = verts[i]
            v1 = verts[(i + 1) % 4]
            # Edge midpoint
            mx = (v0[0] + v1[0]) / 2
            my = (v0[1] + v1[1]) / 2
            # Outward normal from origin (since diamond convex, the midpoint
            # is offset from origin in outward direction)
            nm = math.hypot(mx, my) or 1e-9
            nx = mx / nm
            ny = my / nm
            # Bulged midpoint
            bx = mx + bulge * nx
            by = my + bulge * ny
            # Sample arc through v0, (bx,by), v1 by parametric quadratic Bezier
            for j in range(n_seg):
                t = j / n_seg
                # Quadratic Bezier with control at midpoint pulled outward
                # to (2*bx - mx, 2*by - my) so curve passes through (bx, by) at t=0.5
                cpx = 2 * bx - mx
                cpy = 2 * by - my
                u = 1 - t
                x = u * u * v0[0] + 2 * u * t * cpx + t * t * v1[0]
                y = u * u * v0[1] + 2 * u * t * cpy + t * t * v1[1]
                pts.append((x, y))
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "lobed": True,
                "ref": self.REF,
            },
        )


# 7. simple_gear_outline_plate — gear-like silhouette (no center hole)
class SimpleGearOutlinePlateFamily(BaseFamily):
    name = "simple_gear_outline_plate"
    standard = "N/A"
    REF = "imagined: gear silhouette outline only (no center bore)"

    def sample_params(self, difficulty, rng):
        n_teeth = int(rng.choice([8, 10, 12, 14, 16]))
        r_root = round(float(rng.uniform(20, 40)), 1)
        tooth_h = round(r_root * float(rng.uniform(0.12, 0.22)), 1)
        thickness = round(float(rng.uniform(4, 12)), 1)
        return {
            "n_teeth": n_teeth,
            "r_root": r_root,
            "tooth_h": tooth_h,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["n_teeth"] >= 6
            and p["r_root"] >= 12
            and 1.5 <= p["tooth_h"] <= p["r_root"] * 0.4
            and p["thickness"] >= 2
        )

    def make_program(self, p):
        n = p["n_teeth"]
        r_root = p["r_root"]
        r_tip = r_root + p["tooth_h"]
        # Each tooth = 4 points: root-start, tip-start, tip-end, root-end.
        # Tooth occupies half a sector; gap occupies the other half.
        sector = 2 * math.pi / n
        tooth_w = sector * 0.55  # tooth width fraction of sector
        gap_w = sector - tooth_w
        pts = []
        for k in range(n):
            base = k * sector
            # gap arc start to tooth root (go CCW around root circle for half gap)
            a_root_start = base + gap_w / 2
            a_root_end = a_root_start + tooth_w
            # Tooth: rise from root to tip at a_root_start, stay at tip, drop
            # at a_root_end. Use slightly narrower tip for trapezoidal tooth.
            tip_inset = tooth_w * 0.15
            a_tip_start = a_root_start + tip_inset
            a_tip_end = a_root_end - tip_inset
            pts.append(
                (r_root * math.cos(a_root_start), r_root * math.sin(a_root_start))
            )
            pts.append((r_tip * math.cos(a_tip_start), r_tip * math.sin(a_tip_start)))
            pts.append((r_tip * math.cos(a_tip_end), r_tip * math.sin(a_tip_end)))
            pts.append((r_root * math.cos(a_root_end), r_root * math.sin(a_root_end)))
            # Gap: arc along root from a_root_end to next tooth's a_root_start
            n_gap_pts = 4
            a_gap_end = (k + 1) * sector + gap_w / 2
            for j in range(1, n_gap_pts):
                t = j / n_gap_pts
                a = a_root_end + (a_gap_end - a_root_end) * t
                pts.append((r_root * math.cos(a), r_root * math.sin(a)))
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "gear_outline": True,
                "n_teeth": n,
                "ref": self.REF,
            },
        )


# 8. simple_fan_blade_plate — single fan blade silhouette (asymmetric crescent + tail)
class SimpleFanBladePlateFamily(BaseFamily):
    name = "simple_fan_blade_plate"
    standard = "N/A"
    REF = "imagined: single fan blade silhouette (asymmetric crescent w/ tail)"

    def sample_params(self, difficulty, rng):
        length = round(float(rng.uniform(40, 70)), 1)
        width = round(float(rng.uniform(15, 28)), 1)
        curve = float(rng.uniform(0.20, 0.40))  # bulge of leading edge
        thickness = round(float(rng.uniform(3, 9)), 1)
        return {
            "length": length,
            "width": width,
            "curve": curve,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] >= 25
            and p["width"] >= 8
            and 0.10 <= p["curve"] <= 0.55
            and p["thickness"] >= 1.5
            and p["width"] < p["length"] * 0.7
        )

    def make_program(self, p):
        L = p["length"]
        W = p["width"]
        c = p["curve"] * L
        # Blade: root at (0,0) is small rounded square (the hub-attachment),
        # extends to +X with leading edge curving up (+Y) and trailing edge
        # nearly straight. Tip (at x=L) tapers narrow.
        # Build CCW outline: start at root-bottom (0, -W*0.3), go +X along
        # trailing edge (slightly curved down then up to tip), arc around tip,
        # come back along leading edge (curves up over +Y then back down to root-top).
        n = 30
        pts = []
        # Trailing edge (bottom): from (0, -W*0.3) to (L, -W*0.05), slight S-curve
        for i in range(n + 1):
            t = i / n
            x = L * t
            # Trailing edge has a gentle negative bulge near the middle
            y = -W * 0.3 * (1 - t) + (-W * 0.05) * t - 0.1 * c * math.sin(math.pi * t)
            pts.append((x, y))
        # Tip arc: from (L, -W*0.05) around to (L, W*0.05) — half-circle of
        # tip rounding
        tip_r = W * 0.10
        tip_cx = L - tip_r
        tip_cy = (W * 0.05 + (-W * 0.05)) / 2
        for i in range(1, 12):
            a = -math.pi / 2 + i * math.pi / 12
            pts.append((tip_cx + tip_r * math.cos(a), tip_cy + tip_r * math.sin(a)))
        # Leading edge (top): from (L, W*0.05) back to (0, W*0.3) with a
        # PROMINENT positive bulge near 0.4*L
        for i in range(n + 1):
            t = i / n
            x = L * (1 - t)
            base = W * 0.05 * (1 - t) + W * 0.3 * t
            y = base + c * math.sin(math.pi * (1 - t))
            pts.append((x, y))
        # Root rounding: from (0, W*0.3) back down to (0, -W*0.3) — short
        # near-vertical line is fine.
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "fan_blade": True,
                "ref": self.REF,
            },
        )


# 9. simple_paw_print_plate — main pad + 4 toe pads (union of 5 components)
class SimplePawPrintPlateFamily(BaseFamily):
    name = "simple_paw_print_plate"
    standard = "N/A"
    REF = "imagined: paw-print silhouette (main pad + 4 toes)"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(25, 45)), 1)
        toe_ratio = float(rng.uniform(0.20, 0.30))  # toe radius / scale
        spread = float(rng.uniform(0.55, 0.75))  # toe spread / scale
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "scale": scale,
            "toe_ratio": toe_ratio,
            "spread": spread,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 15
            and 0.12 <= p["toe_ratio"] <= 0.35
            and 0.4 <= p["spread"] <= 0.9
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        T = p["thickness"]
        toe_r = s * p["toe_ratio"]
        spread = s * p["spread"]
        # Main pad: rounded triangle approximated as ellipse-ish closed
        # polyline at origin (lower).
        pad_w = s * 0.6
        pad_h = s * 0.45
        pad_cy = -s * 0.20  # centered below origin
        pad_pts = []
        # Use 36-point ellipse at (0, pad_cy) with semi-axes pad_w/2, pad_h/2
        n_pad = 40
        for i in range(n_pad):
            a = 2 * math.pi * i / n_pad
            pad_pts.append(
                ((pad_w / 2) * math.cos(a), pad_cy + (pad_h / 2) * math.sin(a))
            )
        # Toes: 4 circles arranged in arc above main pad
        # Center toes at angles ~-65, -25, +25, +65 degrees from +Y, on a
        # circle of radius `spread` from origin, ABOVE main pad.
        toe_centers = []
        toe_angles_deg = [-55, -20, 20, 55]
        toe_y_base = s * 0.15  # base for toe placement
        for ad in toe_angles_deg:
            a = math.radians(90 + ad)  # 90° = straight up
            cx = spread * math.cos(a)
            cy = toe_y_base + spread * math.sin(a) - spread  # shift so they form arc
            # That makes them too low. Simpler:
            cx = (spread * 0.9) * math.sin(math.radians(ad))
            cy = s * 0.35 + (spread * 0.15) * (1 - abs(ad) / 70)
            toe_centers.append((cx, cy))

        # Build as union: first sketch is main pad + extrude, then 4 unions
        # of toe circles + extrude.
        ops = _emit_polyline_extrude(pad_pts, T)
        for cx, cy in toe_centers:
            sub_ops = [
                {"name": "center", "args": {"x": _r3(cx), "y": _r3(cy)}},
                {"name": "circle", "args": {"radius": _r3(toe_r)}},
                {"name": "extrude", "args": {"distance": _r3(T)}},
            ]
            ops.append(Op("union", {"ops": sub_ops, "plane": "XY"}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "paw_print": True,
                "ref": self.REF,
            },
        )


# 10. simple_anchor_plate — shaft + ring + 2 sym hooks (union)
class SimpleAnchorPlateFamily(BaseFamily):
    name = "simple_anchor_plate"
    standard = "N/A"
    REF = "imagined: ship anchor outline (shaft + ring + 2 symmetric hooks)"

    def sample_params(self, difficulty, rng):
        scale = round(float(rng.uniform(35, 60)), 1)
        shaft_w_ratio = float(rng.uniform(0.08, 0.13))
        ring_r_ratio = float(rng.uniform(0.18, 0.25))
        hook_r_ratio = float(rng.uniform(0.30, 0.42))
        hook_t_ratio = float(rng.uniform(0.10, 0.15))
        thickness = round(float(rng.uniform(3, 9)), 1)
        return {
            "scale": scale,
            "shaft_w_ratio": shaft_w_ratio,
            "ring_r_ratio": ring_r_ratio,
            "hook_r_ratio": hook_r_ratio,
            "hook_t_ratio": hook_t_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["scale"] >= 25
            and 0.05 <= p["shaft_w_ratio"] <= 0.20
            and 0.12 <= p["ring_r_ratio"] <= 0.30
            and 0.20 <= p["hook_r_ratio"] <= 0.50
            and 0.06 <= p["hook_t_ratio"] <= 0.20
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        s = p["scale"]
        T = p["thickness"]
        shaft_w = s * p["shaft_w_ratio"]
        ring_r = s * p["ring_r_ratio"]
        hook_r = s * p["hook_r_ratio"]
        hook_t = s * p["hook_t_ratio"]

        # Component 1: vertical shaft (rectangle from y=-s/2 to y=ring_top)
        # Ring will be at top, hooks at bottom.
        shaft_top = s * 0.45
        shaft_bot = -s * 0.45
        shaft_rect_pts = [
            (-shaft_w / 2, shaft_bot),
            (shaft_w / 2, shaft_bot),
            (shaft_w / 2, shaft_top - ring_r * 0.5),
            (-shaft_w / 2, shaft_top - ring_r * 0.5),
        ]
        # Component 2: ring (annulus) — but we need solid for union, so use an
        # outer disc; users will visually read it as ring even without hole.
        # To keep it as a closed symbol with NO internal cuts (per spec), we
        # emit a SOLID disc at top.
        ring_cy = shaft_top
        # Component 3: crossbar (horizontal bar near top of shaft, just below ring)
        cross_w = s * 0.55
        cross_h = s * 0.08
        cross_cy = shaft_top - ring_r * 1.3
        cross_pts = [
            (-cross_w / 2, cross_cy - cross_h / 2),
            (cross_w / 2, cross_cy - cross_h / 2),
            (cross_w / 2, cross_cy + cross_h / 2),
            (-cross_w / 2, cross_cy + cross_h / 2),
        ]

        # Component 4 & 5: 2 symmetric hooks at bottom. Each hook is a
        # quarter-arc-like rectangular flag emanating outward from the bottom
        # of the shaft, curving up.
        # Build each hook as a fan (pie-slice + thickness) approximated by polyline:
        # arc center at bottom of shaft (0, shaft_bot), radius hook_r, sweep
        # from straight-down (-90°) to ±horizontal-out (0° or 180°).
        # Use thickness hook_t.
        def hook_pts(side):
            """side=+1 → right hook; side=-1 → left hook."""
            cx = 0.0
            cy = shaft_bot
            if side > 0:
                a0 = math.radians(-90)
                a1 = math.radians(0)
            else:
                a0 = math.radians(180)
                a1 = math.radians(-90)
            n = 20
            ro = hook_r
            ri = hook_r - hook_t
            outer = []
            inner = []
            for i in range(n + 1):
                t = i / n
                a = a0 + (a1 - a0) * t
                outer.append((cx + ro * math.cos(a), cy + ro * math.sin(a)))
                inner.append((cx + ri * math.cos(a), cy + ri * math.sin(a)))
            # Build closed polyline: outer (a0→a1) then inner reversed (a1→a0)
            return outer + list(reversed(inner))

        # Assemble: base shape = shaft rect, union ring disc, crossbar, 2 hooks
        # First op block: shaft rect extrude
        ops = _emit_polyline_extrude(shaft_rect_pts, T)
        # Union ring disc (top)
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "center", "args": {"x": 0.0, "y": _r3(ring_cy)}},
                        {"name": "circle", "args": {"radius": _r3(ring_r)}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                },
            )
        )
        # Union crossbar
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "polyline", "args": {"points": _round_pts(cross_pts)}},
                        {"name": "close", "args": {}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                },
            )
        )
        # Union right hook
        rhook_pts = _round_pts(hook_pts(+1))
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "polyline", "args": {"points": rhook_pts}},
                        {"name": "close", "args": {}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                },
            )
        )
        lhook_pts = _round_pts(hook_pts(-1))
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "polyline", "args": {"points": lhook_pts}},
                        {"name": "close", "args": {}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                },
            )
        )
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "anchor": True,
                "ref": self.REF,
            },
        )


ALL_FAMILIES = [
    SimpleClover3LeafPlateFamily,
    SimpleClover4LeafPlateFamily,
    SimpleFlower5PetalPlateFamily,
    SimpleFlower8PetalPlateFamily,
    SimpleButterflyPlateFamily,
    SimpleDiamondLobedPlateFamily,
    SimpleGearOutlinePlateFamily,
    SimpleFanBladePlateFamily,
    SimplePawPrintPlateFamily,
    SimpleAnchorPlateFamily,
]
