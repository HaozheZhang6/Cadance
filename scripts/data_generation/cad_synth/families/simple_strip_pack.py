"""simple_strip_pack — 10 arc-bar / ribbon / curved-strip families.

Companion to simple_arc_profiles_pack and simple_filleted_pack: covers long
curved/bent strips of constant thickness. Each family builds a 2D outline by
walking a SPINE (arc / wavy line / multi-arc) and offsetting perpendicular by
±strip_t/2 to produce the closed polyline, then a single `extrude(thickness)`.

Distinguished from simple_arc_corner_bracket (sharp L) and simple_filleted_*
(closed shapes) — these are LONG STRIPS.

Family list:
  simple_horseshoe_plate          open ring (270° arc, both ends square)
  simple_arch_plate               semicircle arch outline (Roman arch, open at bottom)
  simple_paperclip_plate          wavy zigzag bar with rounded U-turns
  simple_wave_strip_plate         sinusoidal wave bar (multiple cosine periods)
  simple_serpentine_plate         long S-curve traversing wide extent
  simple_curved_handle_plate      semicircle arch + 2 short straight tabs (door handle)
  simple_bow_tie_plate            two triangles meeting at center (curved bowtie)
  simple_crescent_thick_plate     fat crescent (different proportions from existing)
  simple_lightning_bolt_plate     zigzag with sharp angles (3-segment lightning)
  simple_arc_chain_plate          chain-link silhouette: 3 ovals end-to-end
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- shared helpers --------------------------------------------------


def _r3(x):
    return round(float(x), 3)


def _emit_polyline_extrude(pts, thickness):
    """Standard moveTo + lineTo* + close + extrude."""
    pts_r = [(_r3(x), _r3(y)) for x, y in pts]
    ops = [Op("moveTo", {"x": pts_r[0][0], "y": pts_r[0][1]})]
    for x, y in pts_r[1:]:
        ops.append(Op("lineTo", {"x": x, "y": y}))
    ops += [Op("close", {}), Op("extrude", {"distance": thickness})]
    return ops


def _spine_offset_strip(spine, strip_t, cap_square=True):
    """Build a closed strip outline from spine pts + perpendicular offset.

    spine: list of (x, y) points along the centerline (open curve, not closed)
    strip_t: total strip thickness (offset = ±strip_t/2 each side)
    cap_square: True → flat ends; CCW outline returned

    Returns: list of (x, y) closed polyline (CCW).
    """
    n = len(spine)
    half = strip_t / 2.0
    # Compute perpendicular unit normals at each spine pt (averaged tangents).
    normals = []
    for i in range(n):
        if i == 0:
            tx = spine[1][0] - spine[0][0]
            ty = spine[1][1] - spine[0][1]
        elif i == n - 1:
            tx = spine[n - 1][0] - spine[n - 2][0]
            ty = spine[n - 1][1] - spine[n - 2][1]
        else:
            tx = spine[i + 1][0] - spine[i - 1][0]
            ty = spine[i + 1][1] - spine[i - 1][1]
        L = math.hypot(tx, ty) or 1.0
        # left-hand normal (rotated +90°): (-ty, tx) / L
        nx, ny = -ty / L, tx / L
        normals.append((nx, ny))
    left = [
        (spine[i][0] + half * normals[i][0], spine[i][1] + half * normals[i][1])
        for i in range(n)
    ]
    right = [
        (spine[i][0] - half * normals[i][0], spine[i][1] - half * normals[i][1])
        for i in range(n)
    ]
    # CCW: walk left side forward, then right side backward
    pts = list(left) + list(reversed(right))
    return pts


def _arc_spine(cx, cy, r, a0, a1, n=60):
    """Polyline points along arc from a0 to a1 (radians) around (cx, cy)."""
    return [
        (
            cx + r * math.cos(a0 + (a1 - a0) * i / n),
            cy + r * math.sin(a0 + (a1 - a0) * i / n),
        )
        for i in range(n + 1)
    ]


# ---------- families --------------------------------------------------------


# 1. simple_horseshoe_plate — open ring (270° arc, both ends square)
class SimpleHorseshoePlateFamily(BaseFamily):
    name = "simple_horseshoe_plate"
    standard = "N/A"
    REF = "imagined: U-shaped horseshoe / open ring magnet outline"

    def sample_params(self, difficulty, rng):
        r_mean = round(float(rng.uniform(25, 45)), 1)
        strip_t = round(r_mean * float(rng.uniform(0.18, 0.32)), 1)
        sweep_deg = float(rng.choice([240.0, 260.0, 280.0, 300.0]))
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "r_mean": r_mean,
            "strip_t": strip_t,
            "sweep_deg": sweep_deg,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_mean"] >= 15
            and p["strip_t"] >= 4
            and p["r_mean"] > p["strip_t"] + 4
            and 180 <= p["sweep_deg"] <= 320
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine: arc from a0 to a1 (open at bottom).
        # Center sweep symmetrically around +Y axis: a0 = π/2 - sweep/2,
        # a1 = π/2 + sweep/2 — so the gap is at the bottom.
        sweep = math.radians(p["sweep_deg"])
        a0 = math.pi / 2 - sweep / 2
        a1 = math.pi / 2 + sweep / 2
        spine = _arc_spine(0, 0, p["r_mean"], a0, a1, n=60)
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "open_strip": True,
                "ref": self.REF,
            },
        )


# 2. simple_arch_plate — semicircle arch outline (Roman arch, open at bottom)
class SimpleArchPlateFamily(BaseFamily):
    name = "simple_arch_plate"
    standard = "N/A"
    REF = "imagined: Roman arch / doorway top frame"

    def sample_params(self, difficulty, rng):
        r_mean = round(float(rng.uniform(25, 50)), 1)
        strip_t = round(r_mean * float(rng.uniform(0.15, 0.30)), 1)
        leg_h = round(r_mean * float(rng.uniform(0.4, 1.2)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "r_mean": r_mean,
            "strip_t": strip_t,
            "leg_h": leg_h,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_mean"] >= 15
            and p["strip_t"] >= 4
            and p["r_mean"] > p["strip_t"] + 4
            and p["leg_h"] >= 5
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine: vertical leg (down) → semicircle (180°) → vertical leg (down).
        # Right leg from (r, -leg_h) up to (r, 0), arc CCW 0° → 180° to (-r, 0),
        # left leg down from (-r, 0) to (-r, -leg_h).
        r = p["r_mean"]
        L = p["leg_h"]
        spine = []
        # Right leg, going UP from bottom-right tip to arc start (r, 0).
        n_leg = 16
        for i in range(n_leg + 1):
            spine.append((r, -L + L * i / n_leg))
        # Semicircle arc 0 → π (CCW), skip duplicate first pt
        arc_pts = _arc_spine(0, 0, r, 0.0, math.pi, n=60)
        spine.extend(arc_pts[1:])
        # Left leg, going DOWN from (-r, 0) to (-r, -L)
        for i in range(1, n_leg + 1):
            spine.append((-r, -L * i / n_leg))
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "open_strip": True,
                "ref": self.REF,
            },
        )


# 3. simple_paperclip_plate — wavy zigzag bar with rounded U-turns
class SimplePaperclipPlateFamily(BaseFamily):
    name = "simple_paperclip_plate"
    standard = "N/A"
    REF = "imagined: office paperclip silhouette (multi-loop bend)"

    def sample_params(self, difficulty, rng):
        loop_r = round(float(rng.uniform(8, 16)), 1)
        loop_len = round(loop_r * float(rng.uniform(2.5, 4.5)), 1)
        n_loops = int(rng.choice([2, 3]))
        strip_t = round(loop_r * float(rng.uniform(0.30, 0.55)), 1)
        thickness = round(float(rng.uniform(2, 6)), 1)
        return {
            "loop_r": loop_r,
            "loop_len": loop_len,
            "n_loops": n_loops,
            "strip_t": strip_t,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["loop_r"] >= 5
            and p["loop_len"] >= 2 * p["loop_r"]
            and p["strip_t"] >= 2
            and p["strip_t"] < 1.6 * p["loop_r"]
            and 2 <= p["n_loops"] <= 4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine: row of straight segments connected by half-circle U-turns.
        # Start at (0, 0), go right loop_len, arc up around (loop_len, loop_r),
        # come back left to (0, 2*loop_r), arc up to y=4*loop_r, etc.
        r = p["loop_r"]
        L = p["loop_len"]
        n_loops = p["n_loops"]
        spine = [(0.0, 0.0), (L, 0.0)]
        for k in range(n_loops):
            cy = 2 * r * k + r  # u-turn center y
            cx = L  # right turn
            arc_pts = _arc_spine(cx, cy, r, -math.pi / 2, math.pi / 2, n=40)
            spine.extend(arc_pts[1:])
            # straight segment back to x=0 at y = cy + r
            spine.append((0.0, cy + r))
            # left u-turn (unless this was the last loop)
            if k < n_loops - 1:
                cy2 = cy + 2 * r
                arc_pts2 = _arc_spine(0.0, cy2, r, math.pi / 2, 3 * math.pi / 2, n=40)
                spine.extend(arc_pts2[1:])
                spine.append((L, cy2 + r))
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "zigzag": True,
                "ref": self.REF,
            },
        )


# 4. simple_wave_strip_plate — sinusoidal wave bar (cosine spine)
class SimpleWaveStripPlateFamily(BaseFamily):
    name = "simple_wave_strip_plate"
    standard = "N/A"
    REF = "imagined: sinusoidal wave strip / decorative ripple bar"

    def sample_params(self, difficulty, rng):
        length = round(float(rng.uniform(80, 140)), 1)
        amplitude = round(float(rng.uniform(8, 22)), 1)
        n_periods = int(rng.choice([2, 3, 4]))
        strip_t = round(float(rng.uniform(5, 14)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "length": length,
            "amplitude": amplitude,
            "n_periods": n_periods,
            "strip_t": strip_t,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] >= 40
            and p["amplitude"] >= 3
            and p["amplitude"] < p["length"] / 4
            and p["strip_t"] >= 3
            and p["strip_t"] < p["amplitude"] * 1.3
            and 1 <= p["n_periods"] <= 6
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine: y = A * cos(2π * n_periods * x / L), x ∈ [-L/2, L/2]
        L = p["length"]
        A = p["amplitude"]
        n = p["n_periods"]
        n_pts = 60 * n
        spine = []
        for i in range(n_pts + 1):
            x = -L / 2 + L * i / n_pts
            y = A * math.cos(2 * math.pi * n * x / L)
            spine.append((x, y))
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "wavy": True,
                "ref": self.REF,
            },
        )


# 5. simple_serpentine_plate — long S-curve traversing wide extent
class SimpleSerpentinePlateFamily(BaseFamily):
    name = "simple_serpentine_plate"
    standard = "N/A"
    REF = "imagined: long serpentine cooling channel / multi-period S-bar"

    def sample_params(self, difficulty, rng):
        arc_r = round(float(rng.uniform(15, 30)), 1)
        n_arcs = int(rng.choice([3, 4, 5]))
        strip_t = round(arc_r * float(rng.uniform(0.20, 0.40)), 1)
        thickness = round(float(rng.uniform(3, 9)), 1)
        return {
            "arc_r": arc_r,
            "n_arcs": n_arcs,
            "strip_t": strip_t,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["arc_r"] >= 8
            and p["strip_t"] >= 3
            and p["strip_t"] < p["arc_r"]
            and 2 <= p["n_arcs"] <= 6
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine: series of half-circles tangent end-to-end, alternating direction
        # — like a continuous serpent. Each half-arc spans 180° and shifts by 2r in x.
        r = p["arc_r"]
        n = p["n_arcs"]
        spine = []
        for k in range(n):
            cx = (2 * k + 1) * r  # center of k-th arc
            if k % 2 == 0:
                # bulge up: arc from (2kr, 0) over (cx, +r) to (2(k+1)r, 0), CCW
                arc_pts = _arc_spine(cx, 0.0, r, math.pi, 0.0, n=50)
            else:
                # bulge down: arc from (2kr, 0) under (cx, -r) to (2(k+1)r, 0), CW
                arc_pts = _arc_spine(cx, 0.0, r, math.pi, 2 * math.pi, n=50)
            if k == 0:
                spine.extend(arc_pts)
            else:
                spine.extend(arc_pts[1:])
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "serpentine": True,
                "ref": self.REF,
            },
        )


# 6. simple_curved_handle_plate — semicircle arch + 2 short straight tabs
class SimpleCurvedHandlePlateFamily(BaseFamily):
    name = "simple_curved_handle_plate"
    standard = "N/A"
    REF = "imagined: door pull handle silhouette (arch + 2 mounting tabs)"

    def sample_params(self, difficulty, rng):
        r_mean = round(float(rng.uniform(25, 45)), 1)
        strip_t = round(r_mean * float(rng.uniform(0.16, 0.28)), 1)
        tab_len = round(r_mean * float(rng.uniform(0.25, 0.6)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "r_mean": r_mean,
            "strip_t": strip_t,
            "tab_len": tab_len,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_mean"] >= 15
            and p["strip_t"] >= 4
            and p["r_mean"] > p["strip_t"] + 4
            and p["tab_len"] >= 4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine: short horizontal tab → 180° arch → short horizontal tab,
        # all on one continuous open curve. Like an upside-down U with feet.
        r = p["r_mean"]
        tab = p["tab_len"]
        spine = []
        # Left tab: from (-r - tab, 0) to (-r, 0)
        n_tab = 12
        for i in range(n_tab + 1):
            spine.append((-r - tab + tab * i / n_tab, 0.0))
        # Arch arc: from (-r, 0) over (0, r) to (r, 0), CCW from π → 0
        arc_pts = _arc_spine(0.0, 0.0, r, math.pi, 0.0, n=60)
        spine.extend(arc_pts[1:])
        # Right tab: from (r, 0) to (r + tab, 0)
        for i in range(1, n_tab + 1):
            spine.append((r + tab * i / n_tab, 0.0))
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "open_strip": True,
                "ref": self.REF,
            },
        )


# 7. simple_bow_tie_plate — two triangles meeting at center (curved bowtie)
class SimpleBowTiePlateFamily(BaseFamily):
    name = "simple_bow_tie_plate"
    standard = "N/A"
    REF = "imagined: bow-tie / hourglass plate with curved sides"

    def sample_params(self, difficulty, rng):
        half_w = round(float(rng.uniform(25, 45)), 1)
        end_h = round(half_w * float(rng.uniform(0.6, 1.2)), 1)
        waist = round(end_h * float(rng.uniform(0.18, 0.45)), 1)
        bulge = round(half_w * float(rng.uniform(0.08, 0.20)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "half_w": half_w,
            "end_h": end_h,
            "waist": waist,
            "bulge": bulge,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["half_w"] >= 12
            and p["end_h"] >= 8
            and p["waist"] >= 2
            and p["waist"] < p["end_h"]
            and p["bulge"] >= 1
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Closed bow-tie outline. Sides are 3-point arcs that bulge outward.
        # Corners: (-W, +H/2), (-W, -H/2), waist top (0, +waist/2),
        # waist bot (0, -waist/2), (W, +H/2), (W, -H/2).
        # Path CCW starting (-W, -H/2):
        #   arc up to (-W, +H/2) bulging LEFT through (-W - bulge, 0)
        #   line to waist-top (0, +waist/2)
        #   arc to (W, +H/2) bulging UP — wait, simpler:
        # Just close polyline corners with straight lines and add bulges via arcs.
        # Simplest approach: 8-point closed polyline with bulged ends.
        W = p["half_w"]
        H = p["end_h"]
        wH = p["waist"]
        b = p["bulge"]
        # CCW:
        #   (-W, -H/2) → arc through (-W - b, 0) → (-W, +H/2)
        #   line to (0, +wH/2)
        #   line to (W, +H/2)
        #   arc through (W + b, 0) → (W, -H/2)
        #   line to (0, -wH/2)
        #   close to (-W, -H/2)
        ops = [
            Op("moveTo", {"x": _r3(-W), "y": _r3(-H / 2)}),
            Op(
                "threePointArc",
                {
                    "point1": (_r3(-W - b), _r3(0)),
                    "point2": (_r3(-W), _r3(H / 2)),
                },
            ),
            Op("lineTo", {"x": _r3(0), "y": _r3(wH / 2)}),
            Op("lineTo", {"x": _r3(W), "y": _r3(H / 2)}),
            Op(
                "threePointArc",
                {
                    "point1": (_r3(W + b), _r3(0)),
                    "point2": (_r3(W), _r3(-H / 2)),
                },
            ),
            Op("lineTo", {"x": _r3(0), "y": _r3(-wH / 2)}),
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
                "bowtie": True,
                "ref": self.REF,
            },
        )


# 8. simple_crescent_thick_plate — fat crescent (different proportions)
class SimpleCrescentThickPlateFamily(BaseFamily):
    name = "simple_crescent_thick_plate"
    standard = "N/A"
    REF = "imagined: thick crescent moon / fat C-shape (lower r_inner ratio)"

    def sample_params(self, difficulty, rng):
        # Thicker than simple_crescent_plate: lower r_inner ratio + larger offset.
        r_outer = round(float(rng.uniform(30, 55)), 1)
        # r_inner ratio 0.55 .. 0.78 (vs existing 0.5 .. 0.85)
        ratio = float(rng.uniform(0.55, 0.78))
        r_inner = round(r_outer * ratio, 1)
        # offset 0.30 .. 0.55 of r_outer (vs existing 0.15 .. 0.35) — fatter crescent
        offset = round(r_outer * float(rng.uniform(0.30, 0.55)), 1)
        thickness = round(float(rng.uniform(4, 14)), 1)
        return {
            "r_outer": r_outer,
            "r_inner": r_inner,
            "offset": offset,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        # Valid crescent requires r_inner < r_outer (else inner consumes outer)
        # AND offset + r_inner > r_outer (else inner sits inside outer = annulus, not crescent).
        # AND r_outer - offset > 0 (some "fat" rim remains on opposite side of offset).
        return (
            p["r_outer"] > p["r_inner"] + 4
            and p["r_inner"] >= 8
            and p["offset"] >= 4
            and p["offset"] + p["r_inner"] > p["r_outer"]
            and p["r_outer"] - p["offset"] > 4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Closed outline: outer 180° arc CCW + inner 180° arc CW (offset center).
        # Polyline approx (n=40 each), starting at (r_outer, 0).
        ro = p["r_outer"]
        ri = p["r_inner"]
        off = p["offset"]
        n = 40
        pts = []
        # outer arc 0 → π (CCW, top half)
        for i in range(n + 1):
            a = math.pi * i / n
            pts.append((ro * math.cos(a), ro * math.sin(a)))
        # inner arc π → 0 (CW, top half), centered at (off, 0)
        for i in range(1, n + 1):
            a = math.pi - math.pi * i / n
            pts.append((off + ri * math.cos(a), ri * math.sin(a)))
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "crescent_thick": True,
                "ref": self.REF,
            },
        )


# 9. simple_lightning_bolt_plate — zigzag with sharp angles (3-segment)
class SimpleLightningBoltPlateFamily(BaseFamily):
    name = "simple_lightning_bolt_plate"
    standard = "N/A"
    REF = "imagined: lightning bolt / zigzag arrow (3 sharp segments)"

    def sample_params(self, difficulty, rng):
        seg_len = round(float(rng.uniform(25, 45)), 1)
        zigzag = round(seg_len * float(rng.uniform(0.45, 0.85)), 1)
        strip_t = round(float(rng.uniform(6, 14)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "seg_len": seg_len,
            "zigzag": zigzag,
            "strip_t": strip_t,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["seg_len"] >= 12
            and p["zigzag"] >= 8
            and p["strip_t"] >= 4
            and p["strip_t"] < p["seg_len"] * 0.6
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Spine is 3 connected straight segments forming a zigzag:
        #   (0, 0) → (zigzag, seg_len) → (-zigzag, 2*seg_len) → (zigzag, 3*seg_len)
        # Sample each segment with intermediate pts to keep normal-averaging stable.
        seg = p["seg_len"]
        z = p["zigzag"]
        anchors = [
            (0.0, 0.0),
            (z, seg),
            (-z, 2 * seg),
            (z, 3 * seg),
        ]
        spine = []
        n_per_seg = 8
        for k in range(len(anchors) - 1):
            x0, y0 = anchors[k]
            x1, y1 = anchors[k + 1]
            for i in range(n_per_seg + 1):
                t = i / n_per_seg
                if k > 0 and i == 0:
                    continue
                spine.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        pts = _spine_offset_strip(spine, p["strip_t"])
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "zigzag": True,
                "ref": self.REF,
            },
        )


# 10. simple_arc_chain_plate — chain-link silhouette: 3 ovals end-to-end
class SimpleArcChainPlateFamily(BaseFamily):
    name = "simple_arc_chain_plate"
    standard = "N/A"
    REF = "imagined: chain-link silhouette / 3 ovals connected end-to-end"

    def sample_params(self, difficulty, rng):
        link_len = round(float(rng.uniform(35, 55)), 1)
        link_w = round(link_len * float(rng.uniform(0.35, 0.55)), 1)
        strip_t = round(link_w * float(rng.uniform(0.20, 0.35)), 1)
        n_links = int(rng.choice([2, 3, 4]))
        thickness = round(float(rng.uniform(3, 10)), 1)
        return {
            "link_len": link_len,
            "link_w": link_w,
            "strip_t": strip_t,
            "n_links": n_links,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["link_len"] >= 20
            and p["link_w"] >= 8
            and p["strip_t"] >= 2
            and p["strip_t"] < p["link_w"] / 2
            and 2 <= p["n_links"] <= 5
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # We render the chain as a single closed outer outline (no inner holes).
        # Outline = stack of overlapping stadium silhouettes, but to keep it
        # a single simple closed polyline we instead draw a long horizontal
        # stadium-cluster: alternating arcs at each link end + straight sides.
        # Simplest: take the outer convex hull of n stadiums shifted by
        # (link_len - link_w) along x, alternating axis 0/90°. Hard.
        # Instead use a cleaner topology: chain SILHOUETTE = a single tall thin
        # stadium with `n_links` rounded bumps along the top and bottom (where
        # the perpendicular links would have crossed). Even simpler: just make
        # a horizontal stadium of length n_links * (link_len - link_w) + link_w
        # with `n_links - 1` round notches on top and bottom ("waist" between
        # adjacent links). This gives the recognizable "chain" silhouette.
        Llink = p["link_len"]
        W = p["link_w"]
        n_links = p["n_links"]
        notch_r = W * 0.20  # subtle waist
        # Total stadium length: n_links links of length Llink each, overlap by W
        # at every join.
        total_L = n_links * Llink - (n_links - 1) * W
        half_L = total_L / 2
        half_W = W / 2
        end_r = half_W  # stadium ends are semicircles
        n_arc = 30
        pts = []
        # Walk outline CCW:
        # 1) bottom edge from left-end semicircle through notches to right-end
        # Left end: semicircle from (-half_L + end_r, -half_W) going down/left
        # to (-half_L + end_r, +half_W). We instead compose:
        # Start at right top corner (just before right semicircle), work CCW.
        # Actually easiest: build an oval with `n_links - 1` notches indented on
        # each long side at every link join.
        # Step (a): top edge LEFT→RIGHT with notches:
        # left semicircle start at (-half_L + end_r, +half_W), top
        # but easier: start at (+half_L - end_r, +half_W), walk LEFT.
        x_top_right = half_L - end_r
        x_top_left = -half_L + end_r
        # top edge points (with notches dipping down at each join)
        top_pts = []
        # Walk from x_top_right LEFT to x_top_left along y=+half_W with notches.
        # Joins at x_join_k = x_top_right - k * (Llink - W) for k=1..n_links-1
        joins = [x_top_right - k * (Llink - W) for k in range(1, n_links)]
        # Add right corner first (start point of polyline here)
        top_pts.append((x_top_right, half_W))
        for xj in joins:
            # approach notch
            top_pts.append((xj + notch_r, half_W))
            # notch dip — small semicircle dipping DOWN to y=half_W - notch_r
            for i in range(1, n_arc):
                a = i * math.pi / n_arc
                # arc from (xj+notch_r, half_W) through (xj, half_W-notch_r)
                # to (xj-notch_r, half_W). Center (xj, half_W), radius notch_r,
                # angle 0 → π going CW (downward).
                ang = -a  # 0 → -π
                top_pts.append(
                    (xj + notch_r * math.cos(ang), half_W + notch_r * math.sin(ang))
                )
            top_pts.append((xj - notch_r, half_W))
        top_pts.append((x_top_left, half_W))
        # left semicircle from (x_top_left, half_W) → (x_top_left, -half_W),
        # bulging LEFT through (-half_L, 0).
        left_arc = []
        for i in range(1, n_arc):
            a = math.pi / 2 + i * math.pi / n_arc  # π/2 → 3π/2
            left_arc.append((x_top_left + end_r * math.cos(a), 0 + end_r * math.sin(a)))
        # bottom edge from (x_top_left, -half_W) → (x_top_right, -half_W),
        # with notches BUMPING UP (concave from outside)
        bottom_pts = [(x_top_left, -half_W)]
        for xj in reversed(joins):
            bottom_pts.append((xj - notch_r, -half_W))
            for i in range(1, n_arc):
                a = i * math.pi / n_arc
                # arc 0 → π CCW upward (going RIGHT along x_axis-mirror)
                ang = math.pi - a  # so it sweeps the upper half from inside view
                # actually we want bottom edge to bulge UP (toward +y) at notch.
                # Center (xj, -half_W), radius notch_r, going through (xj, -half_W + notch_r)
                # parameterize: start at (xj-notch_r, -half_W) [a=π] go through
                # (xj, -half_W+notch_r) [a=π/2] to (xj+notch_r, -half_W) [a=0]
                a2 = math.pi - i * math.pi / n_arc
                bottom_pts.append(
                    (xj + notch_r * math.cos(a2), -half_W + notch_r * math.sin(a2))
                )
            bottom_pts.append((xj + notch_r, -half_W))
        bottom_pts.append((x_top_right, -half_W))
        # right semicircle from (x_top_right, -half_W) → (x_top_right, half_W),
        # bulging RIGHT through (half_L, 0).
        right_arc = []
        for i in range(1, n_arc):
            a = -math.pi / 2 + i * math.pi / n_arc  # -π/2 → π/2
            right_arc.append(
                (x_top_right + end_r * math.cos(a), 0 + end_r * math.sin(a))
            )
        # Assemble (CCW): top from right→left, left arc, bottom from left→right,
        # right arc, close.
        # But we started at top_right going LEFT, which is the +x→-x direction
        # along y=+half_W: that's going CW around the shape (since +y is up and
        # we're moving -x).  Hmm wait, CCW around the shape from top-right corner
        # goes UP-LEFT first... but we're staying on top edge moving left → this
        # is the CCW direction along the TOP edge. After top edge we hit
        # top-left, then go DOWN via left arc → bottom-left, then RIGHT along
        # bottom → bottom-right, then UP via right arc → top-right.  That's CCW
        # — good.
        # NOTE: top-edge notches dip DOWN (into the shape) — this makes them
        # concave. Bottom-edge notches bump UP (also into the shape) — concave.
        # That gives the "chain join" waist look.
        pts = top_pts + left_arc + bottom_pts + right_arc
        # First point: (x_top_right, half_W). After right_arc the last pt is
        # at angle ≈ +π/2 - tiny → close back to start.
        ops = _emit_polyline_extrude(pts, p["thickness"])
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "sketch_arc": True,
                "chain": True,
                "ref": self.REF,
            },
        )


ALL_FAMILIES = [
    SimpleHorseshoePlateFamily,
    SimpleArchPlateFamily,
    SimplePaperclipPlateFamily,
    SimpleWaveStripPlateFamily,
    SimpleSerpentinePlateFamily,
    SimpleCurvedHandlePlateFamily,
    SimpleBowTiePlateFamily,
    SimpleCrescentThickPlateFamily,
    SimpleLightningBoltPlateFamily,
    SimpleArcChainPlateFamily,
]
