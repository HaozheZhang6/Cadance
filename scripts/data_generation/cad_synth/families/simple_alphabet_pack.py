"""simple_alphabet_pack — extruded capital-letter / number nameplate shapes.

Each family models a single character as a thick-stroke 2D outline extruded
along Z.  Strokes are constant-thickness rectangles (and arcs where required)
unioned together to form the letter silhouette.

Family list:
  simple_letter_l_plate     L  — vertical bar + bottom horizontal foot
  simple_letter_t_plate     T  — horizontal top + vertical descender
  simple_letter_h_plate     H  — 2 verticals + 1 cross-bar
  simple_letter_e_plate     E  — vertical spine + 3 horizontal arms
  simple_letter_f_plate     F  — vertical spine + 2 horizontal arms (top/mid)
  simple_letter_p_plate     P  — vertical spine + closed bowl on upper half
  simple_letter_d_plate     D  — vertical spine + half-disc bowl on right
  simple_letter_u_plate     U  — vertical + arc bottom + vertical
  simple_letter_j_plate     J  — vertical + small arc hook at bottom
  simple_letter_y_plate     Y  — V branching + vertical descender
  simple_letter_x_plate     X  — 2 diagonals crossing at center
  simple_number_8_plate     8  — figure 8 (two stacked annular rings)

Op vocabulary (see pipeline/builder.py):
  rect, circle, extrude, union, transformed, polyline, threePointArc,
  moveTo, lineTo, close.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- shared helpers --------------------------------------------------


def _r3(x):
    return round(float(x), 3)


def _round_pt(p):
    return (_r3(p[0]), _r3(p[1]))


def _rect_at(cx, cy, length, width, thickness):
    """Sub-ops list: place rect of (length × width) centered at (cx,cy), extrude."""
    return [
        {
            "name": "transformed",
            "args": {"offset": [_r3(cx), _r3(cy), 0], "rotate": [0, 0, 0]},
        },
        {"name": "rect", "args": {"length": _r3(length), "width": _r3(width)}},
        {"name": "extrude", "args": {"distance": _r3(thickness)}},
    ]


def _rect_rot_at(cx, cy, length, width, thickness, angle_deg):
    """Sub-ops list: rotated rect centered at (cx,cy), z-rotation in degrees."""
    return [
        {
            "name": "transformed",
            "args": {
                "offset": [_r3(cx), _r3(cy), 0],
                "rotate": [0, 0, _r3(angle_deg)],
            },
        },
        {"name": "rect", "args": {"length": _r3(length), "width": _r3(width)}},
        {"name": "extrude", "args": {"distance": _r3(thickness)}},
    ]


# ---------- families --------------------------------------------------------


# 1. simple_letter_l_plate — capital L
class SimpleLetterLPlateFamily(BaseFamily):
    name = "simple_letter_l_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'L' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.55, 0.75)), 1)
        stroke = round(h * float(rng.uniform(0.18, 0.27)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 20
            and p["width"] >= 12
            and 3 <= p["stroke"] < min(p["height"], p["width"]) * 0.5
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        # Vertical bar: anchored at left, full height
        ops = [
            Op("rect", {"length": s, "width": H}),
            Op("extrude", {"distance": T}),
            # Horizontal foot at bottom: from left edge to width W
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=(W - s) / 2.0,
                        cy=-(H - s) / 2.0,
                        length=W - s,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "L", "ref": self.REF},
        )


# 2. simple_letter_t_plate — capital T
class SimpleLetterTPlateFamily(BaseFamily):
    name = "simple_letter_t_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'T' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.6, 0.95)), 1)
        stroke = round(h * float(rng.uniform(0.16, 0.25)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 20
            and p["width"] >= 15
            and 3 <= p["stroke"] < min(p["height"], p["width"]) * 0.5
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        # Horizontal top bar centered at top
        ops = [
            Op("rect", {"length": W, "width": s}),
            Op("extrude", {"distance": T}),
            # Vertical descender centered, hanging below top
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=0.0,
                        cy=-(H - s) / 2.0,
                        length=s,
                        width=H - s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "T", "ref": self.REF},
        )


# 3. simple_letter_h_plate — capital H
class SimpleLetterHPlateFamily(BaseFamily):
    name = "simple_letter_h_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'H' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.55, 0.85)), 1)
        stroke = round(h * float(rng.uniform(0.16, 0.24)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 20
            and p["width"] >= 15
            and 3 <= p["stroke"] < min(p["height"], p["width"]) * 0.4
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        # Left vertical
        ops = [
            Op("rect", {"length": s, "width": H}),
            Op("extrude", {"distance": T}),
            # Right vertical
            Op(
                "union",
                {
                    "ops": _rect_at(cx=W - s, cy=0.0, length=s, width=H, thickness=T),
                    "plane": "XY",
                },
            ),
            # Horizontal cross-bar at mid-height
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=(W - s) / 2.0,
                        cy=0.0,
                        length=W - s,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "H", "ref": self.REF},
        )


# 4. simple_letter_e_plate — capital E (spine + 3 horizontal arms)
class SimpleLetterEPlateFamily(BaseFamily):
    name = "simple_letter_e_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'E' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.55, 0.8)), 1)
        stroke = round(h * float(rng.uniform(0.13, 0.20)), 1)
        # middle arm shorter than top/bottom (typographic convention)
        mid_ratio = float(rng.uniform(0.7, 0.95))
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "mid_ratio": mid_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["width"] >= 15
            and 3 <= p["stroke"] < p["height"] * 0.30
            and p["thickness"] >= 1.5
            and 0.5 <= p["mid_ratio"] <= 1.0
            # 3 arms must fit without overlap: 3·s < H
            and 3 * p["stroke"] < p["height"]
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        mid_w = (W - s) * p["mid_ratio"]
        # Spine
        ops = [
            Op("rect", {"length": s, "width": H}),
            Op("extrude", {"distance": T}),
            # Top arm
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=(W - s) / 2.0,
                        cy=(H - s) / 2.0,
                        length=W - s,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
            # Bottom arm
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=(W - s) / 2.0,
                        cy=-(H - s) / 2.0,
                        length=W - s,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
            # Middle arm (shorter)
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=mid_w / 2.0,
                        cy=0.0,
                        length=mid_w,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "E", "ref": self.REF},
        )


# 5. simple_letter_f_plate — capital F (spine + top + middle, no bottom)
class SimpleLetterFPlateFamily(BaseFamily):
    name = "simple_letter_f_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'F' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.55, 0.8)), 1)
        stroke = round(h * float(rng.uniform(0.13, 0.20)), 1)
        mid_ratio = float(rng.uniform(0.65, 0.9))
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "mid_ratio": mid_ratio,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["width"] >= 15
            and 3 <= p["stroke"] < p["height"] * 0.30
            and p["thickness"] >= 1.5
            and 0.5 <= p["mid_ratio"] <= 1.0
            and 2 * p["stroke"] < p["height"]
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        mid_w = (W - s) * p["mid_ratio"]
        # Place middle arm slightly above center for typographic balance
        mid_y = H * 0.10
        ops = [
            Op("rect", {"length": s, "width": H}),
            Op("extrude", {"distance": T}),
            # Top arm
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=(W - s) / 2.0,
                        cy=(H - s) / 2.0,
                        length=W - s,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
            # Middle arm (shorter)
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=mid_w / 2.0,
                        cy=mid_y,
                        length=mid_w,
                        width=s,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "F", "ref": self.REF},
        )


# 6. simple_letter_p_plate — capital P (spine + closed bowl on upper half)
class SimpleLetterPPlateFamily(BaseFamily):
    name = "simple_letter_p_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'P' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        # Bowl width is roughly half the letter height
        bowl_d = round(h * float(rng.uniform(0.45, 0.6)), 1)
        stroke = round(h * float(rng.uniform(0.14, 0.20)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "bowl_d": bowl_d,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["bowl_d"] >= 12
            and 3 <= p["stroke"] < p["bowl_d"] * 0.45
            and p["bowl_d"] < p["height"] * 0.7
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, bd, s, T = p["height"], p["bowl_d"], p["stroke"], p["thickness"]
        # Spine (full height)
        ops = [
            Op("rect", {"length": s, "width": H}),
            Op("extrude", {"distance": T}),
        ]
        # Bowl: an annular half-disc on the upper half of the spine.
        # Outer disc radius R = bd/2, inner radius R - s.
        # Bowl center attaches to the spine at (s/2, H/2 - R).
        R = bd / 2.0
        cx = s / 2.0
        cy = H / 2.0 - R
        ri = R - s
        # Outer disc
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [_r3(cx), _r3(cy), 0],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "circle", "args": {"radius": _r3(R)}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                    "plane": "XY",
                },
            )
        )
        # Cut inner disc to make the bowl hollow
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [_r3(cx), _r3(cy), 0],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "circle", "args": {"radius": _r3(ri)}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                    "plane": "XY",
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
                "letter": "P",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 7. simple_letter_d_plate — capital D (spine + half-disc bowl on right)
class SimpleLetterDPlateFamily(BaseFamily):
    name = "simple_letter_d_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'D' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        bowl_w = round(h * float(rng.uniform(0.45, 0.65)), 1)
        stroke = round(h * float(rng.uniform(0.14, 0.20)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "bowl_w": bowl_w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["bowl_w"] >= 12
            and 3 <= p["stroke"] < p["bowl_w"] * 0.45
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, bw, s, T = p["height"], p["bowl_w"], p["stroke"], p["thickness"]
        # Outer ellipse half (right side) attached to vertical spine.
        # Implementation: outer outline polyline with right side as 11-pt arc,
        # left side as straight vertical edge of spine.  Inner cut: ellipse-half
        # of (xRadius=bw-s, yRadius=H/2-s).
        rx_o = bw
        ry_o = H / 2.0
        rx_i = max(2.0, bw - s)
        ry_i = max(2.0, H / 2.0 - s)
        # Outer outline traced CCW: start at (0, +H/2), down spine left edge to
        # (-s, +H/2)... actually we want the spine on the LEFT of the letter
        # body.  Place D bounded in x ∈ [0, bw], y ∈ [-H/2, +H/2].
        # Spine occupies x ∈ [0, s], full height.  Bowl is a half-ellipse
        # bulging from x=0 to x=bw on the right.
        # Outer outline (CCW): (0, H/2) → arc through (bw, 0) → (0, -H/2)
        #                      → (-0, -H/2)  — actually we need to extend the
        # spine rectangle to the LEFT of x=0.  Re-anchor: spine x ∈ [-s/2, s/2].
        # Bowl half-ellipse from (s/2, H/2) bulging right to (s/2, -H/2).
        n_arc = 12
        outer_pts = [(_r3(s / 2.0), _r3(H / 2.0))]
        for i in range(1, n_arc):
            theta = math.pi / 2 - (i / n_arc) * math.pi  # +π/2 → -π/2
            outer_pts.append(
                (_r3(s / 2.0 + rx_o * math.cos(theta)), _r3(ry_o * math.sin(theta)))
            )
        outer_pts.append((_r3(s / 2.0), _r3(-H / 2.0)))
        outer_pts.append((_r3(-s / 2.0), _r3(-H / 2.0)))
        outer_pts.append((_r3(-s / 2.0), _r3(H / 2.0)))
        ops = [
            Op("polyline", {"points": outer_pts}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
        ]
        # Inner cut: a half-ellipse bowl on the right of the spine.
        # Build inner profile: vertical line on left at x=s/2, half-ellipse on
        # right with radii (rx_i, ry_i), centered at (s/2, 0).
        inner_pts = [(_r3(s / 2.0), _r3(ry_i))]
        for i in range(1, n_arc):
            theta = math.pi / 2 - (i / n_arc) * math.pi
            inner_pts.append(
                (_r3(s / 2.0 + rx_i * math.cos(theta)), _r3(ry_i * math.sin(theta)))
            )
        inner_pts.append((_r3(s / 2.0), _r3(-ry_i)))
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {"name": "polyline", "args": {"points": inner_pts}},
                        {"name": "close", "args": {}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                    "plane": "XY",
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
                "letter": "D",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 8. simple_letter_u_plate — capital U (vertical + arc bottom + vertical)
class SimpleLetterUPlateFamily(BaseFamily):
    name = "simple_letter_u_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'U' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.6, 0.9)), 1)
        stroke = round(h * float(rng.uniform(0.13, 0.20)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["width"] >= 15
            and 3 <= p["stroke"] < p["width"] * 0.4
            and p["thickness"] >= 1.5
            # vertical leg height must remain positive after subtracting bottom
            # half-circle of radius w/2
            and p["height"] > p["width"] * 0.5 + p["stroke"]
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        # Outer outline of U: rectangle (W × H) with bottom replaced by a
        # half-circle bulging downward (so the outer bottom is rounded).
        # Inner cutout: smaller rectangle (W-2s × H-s) with bottom half-circle.
        ro = W / 2.0  # outer half-circle radius (= half of outer width)
        ri = ro - s
        # leg length = vertical-straight portion length = H - ro
        # Outer profile (CCW, starting at top-left):
        #   (-ro, +H/2 - ro) ?  No — we anchor U with top edges of the legs at
        #   y = +H/2, bottom of arc reaches y = +H/2 - H = -H/2.
        # Let top of legs = +H/2, bottom of outer arc = -H/2.
        # leg straight portion goes from y = +H/2 to y = -H/2 + ro (transition
        # point where arc starts).  Arc center at (0, -H/2 + ro).
        top_y = H / 2.0
        arc_cy = -H / 2.0 + ro
        # Outer outline (CCW): start top-left (-ro, top_y) → top-right (ro, top_y)
        # → down right leg to (ro, arc_cy) → arc to (-ro, arc_cy) through (0, -H/2)
        # → up left leg back to (-ro, top_y).
        ops = [
            Op("moveTo", {"x": _r3(-ro), "y": _r3(top_y)}),
            Op("lineTo", {"x": _r3(ro), "y": _r3(top_y)}),
            Op("lineTo", {"x": _r3(ro), "y": _r3(arc_cy)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((0.0, -H / 2.0)),
                    "point2": _round_pt((-ro, arc_cy)),
                },
            ),
            Op("close", {}),
            Op("extrude", {"distance": T}),
        ]
        # Inner cut: same shape but smaller — top opens upward, so cut profile
        # extends ABOVE the part by epsilon to ensure cut-thru.  Inner top is
        # also at top_y (so we cut all the way through the top opening).
        eps = 0.5
        inner_top = top_y + eps  # extend above to guarantee cut-through
        inner_arc_cy = -H / 2.0 + ro + (s - 0)  # raise inner arc by s
        # Wait — inner arc radius = ri.  Inner arc center at (0, inner_arc_cy).
        # inner_arc_cy must place the BOTTOM of inner arc at y = -H/2 + s.
        inner_arc_cy = -H / 2.0 + s + ri
        inner_pts_ops = [
            {
                "name": "moveTo",
                "args": {"x": _r3(-ri), "y": _r3(inner_top)},
            },
            {
                "name": "lineTo",
                "args": {"x": _r3(ri), "y": _r3(inner_top)},
            },
            {
                "name": "lineTo",
                "args": {"x": _r3(ri), "y": _r3(inner_arc_cy)},
            },
            {
                "name": "threePointArc",
                "args": {
                    "point1": _round_pt((0.0, -H / 2.0 + s)),
                    "point2": _round_pt((-ri, inner_arc_cy)),
                },
            },
            {"name": "close", "args": {}},
            {"name": "extrude", "args": {"distance": _r3(T + 2 * eps)}},
        ]
        ops.append(Op("cut", {"ops": inner_pts_ops, "plane": "XY"}))
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "letter": "U",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 9. simple_letter_j_plate — capital J (vertical + small arc hook at bottom)
class SimpleLetterJPlateFamily(BaseFamily):
    name = "simple_letter_j_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'J' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        # stroke first; hook radius must comfortably exceed stroke
        stroke = round(h * float(rng.uniform(0.10, 0.16)), 1)
        # hook radius >= 2.2 × stroke so a half-ring can be drawn cleanly
        hook_r = round(stroke * float(rng.uniform(2.4, 3.5)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "hook_r": hook_r,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["hook_r"] >= 6
            and 3 <= p["stroke"] < p["hook_r"] * 0.55
            and p["thickness"] >= 1.5
            and p["height"] > 2 * p["hook_r"]
        )

    def make_program(self, p):
        H, hr, s, T = p["height"], p["hook_r"], p["stroke"], p["thickness"]
        # J = vertical bar (top portion) + half-hook (bottom-left half-ring).
        # Vertical bar centered at x=hr (so bar's right edge has x = hr + s/2).
        # Hook is a half-ring centered at (hr, -H/2 + hr) with outer r = hr,
        # inner r = hr - s, sweeping the LOWER half (180° arc from a=0 to a=π)
        # — actually we want the hook to swing from the bar bottom around to the
        # left.  Bar bottom is at (hr + s/2, -H/2 + hr).  Hook outer arc goes
        # from (hr + s/2, -H/2 + hr)? no — the bar continues straight, then
        # transitions into a quarter-circle at the bottom that wraps left.
        # Cleanest J: outer outline traced CCW:
        #   (top_right) (hr + s/2, +H/2)
        #   → (bottom_right of straight) (hr + s/2, -H/2 + hr)
        #   → arc (CCW) through (0, -H/2) to (-hr, -H/2 + hr)   [outer hook arc]
        #   → up to (-hr + s, -H/2 + hr)? no — inner hook end at (-hr + s, -H/2 + hr)
        #   → arc (CW) back through (0, -H/2 + s) to (hr - s, -H/2 + hr)
        #   → up to (hr - s/2, +H/2)... wait, the bar width = s, so its left
        #   edge is at hr - s/2.
        # Re-derive: bar centered at x=0, width s.  Hook center at (-hr + s/2, -H/2 + hr).
        # That places the OUTER edge of the bar at x = +s/2, and the hook
        # extends LEFT of the bar reaching outer left at x = -hr + s/2 - hr =
        # -2hr + s/2.  That's too far left.
        # Better: hook center coincides with bar's center-x but shifted to put
        # the hook curl going leftward.  Bar at x ∈ [-s/2, s/2].  Hook center
        # at (0, -H/2 + hr): outer arc radius = hr + s/2 (extending to right
        # by hr + s/2 and left by hr + s/2).  But we only want hook on ONE side
        # (left).  So: bar at x ∈ [hr - s, hr] (right-aligned at x=hr),
        # hook center at (hr - hr, -H/2 + hr) = (0, -H/2 + hr) with outer radius hr.
        # Top-right of bar: (hr, H/2).  Bottom-right of bar straight: (hr, -H/2 + hr).
        # Outer arc CCW from (hr, -H/2 + hr) through (0, -H/2) to (-hr, -H/2 + hr).
        # Then UP slightly by s to (-hr, -H/2 + hr + 0)? no — the hook tip
        # ENDS at (-hr, -H/2 + hr) on the outer side.  Inner side: from there
        # we step INWARD by s (toward arc center) to (-hr + s, -H/2 + hr).
        # Then arc CW back through (0, -H/2 + s) to (hr - s, -H/2 + hr).
        # Then UP straight to (hr - s, +H/2) (top-left of bar).
        # Then close to (hr, +H/2).
        bar_xR = hr  # bar right edge x
        bar_xL = hr - s  # bar left edge x
        cy = -H / 2.0 + hr
        ops = [
            Op("moveTo", {"x": _r3(bar_xR), "y": _r3(H / 2.0)}),
            Op("lineTo", {"x": _r3(bar_xR), "y": _r3(cy)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((0.0, -H / 2.0)),
                    "point2": _round_pt((-hr, cy)),
                },
            ),
            Op("lineTo", {"x": _r3(-hr + s), "y": _r3(cy)}),
            Op(
                "threePointArc",
                {
                    "point1": _round_pt((0.0, -H / 2.0 + s)),
                    "point2": _round_pt((bar_xL, cy)),
                },
            ),
            Op("lineTo", {"x": _r3(bar_xL), "y": _r3(H / 2.0)}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "letter": "J",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


# 10. simple_letter_y_plate — capital Y (V branching + descender)
class SimpleLetterYPlateFamily(BaseFamily):
    name = "simple_letter_y_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'Y' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.55, 0.85)), 1)
        stroke = round(h * float(rng.uniform(0.13, 0.20)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["width"] >= 15
            and 3 <= p["stroke"] < p["width"] * 0.35
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        # Y = upper-half V (two diagonals from top corners meeting at center)
        #     + lower-half vertical descender.
        # Upper V occupies y ∈ [0, H/2], bottom descender y ∈ [-H/2, 0].
        # Diagonal length: from (W/2, H/2) to (0, 0).  Length = sqrt((W/2)^2 + (H/2)^2).
        diag_len = math.hypot(W / 2.0, H / 2.0)
        diag_angle = math.degrees(math.atan2(H / 2.0, W / 2.0))
        # Right diagonal: centered at (W/4, H/4), rotated by -diag_angle (so
        # rect lies along the line from (0,0) to (W/2, H/2)).
        ops = [
            # Vertical descender (lower half + a bit overlap into the junction)
            Op("rect", {"length": s, "width": H / 2.0 + s}),
            Op("extrude", {"distance": T}),
        ]
        # Place descender properly: rect of (s × (H/2 + s)) centered at
        # (0, -H/4 + s/2)? — its center should be at y = -H/4 + s/2 so its top
        # is at y = -H/4 + s/2 + (H/2 + s)/2 = -H/4 + s/2 + H/4 + s/2 = s.
        # We want its top to overlap a bit above origin (so junction with V is
        # solid).  Recenter:
        # Replace first rect to have proper position:
        ops = [
            # Right diagonal arm: rect length = diag_len, width = s, rotated by -diag_angle
            Op(
                "transformed",
                {
                    "offset": [_r3(W / 4.0), _r3(H / 4.0), 0],
                    "rotate": [0, 0, _r3(-diag_angle)],
                },
            ),
            Op("rect", {"length": _r3(diag_len + s), "width": s}),
            Op("extrude", {"distance": T}),
            # Left diagonal arm
            Op(
                "union",
                {
                    "ops": _rect_rot_at(
                        cx=-W / 4.0,
                        cy=H / 4.0,
                        length=diag_len + s,
                        width=s,
                        thickness=T,
                        angle_deg=+diag_angle,
                    ),
                    "plane": "XY",
                },
            ),
            # Vertical descender from (0, -H/2) up to (0, +s/2) (some overlap)
            Op(
                "union",
                {
                    "ops": _rect_at(
                        cx=0.0,
                        cy=-H / 4.0 + s / 4.0,
                        length=s,
                        width=H / 2.0 + s / 2.0,
                        thickness=T,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "Y", "ref": self.REF},
        )


# 11. simple_letter_x_plate — capital X (2 diagonals crossing)
class SimpleLetterXPlateFamily(BaseFamily):
    name = "simple_letter_x_plate"
    standard = "N/A"
    REF = "imagined: capital letter 'X' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        h = round(float(rng.uniform(30, 55)), 1)
        w = round(h * float(rng.uniform(0.55, 0.85)), 1)
        stroke = round(h * float(rng.uniform(0.12, 0.20)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "height": h,
            "width": w,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["height"] >= 25
            and p["width"] >= 15
            and 3 <= p["stroke"] < p["width"] * 0.35
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        H, W, s, T = p["height"], p["width"], p["stroke"], p["thickness"]
        diag_len = math.hypot(W, H)
        diag_angle = math.degrees(math.atan2(H, W))
        ops = [
            # Diagonal from bottom-left to top-right
            Op(
                "transformed",
                {"offset": [0, 0, 0], "rotate": [0, 0, _r3(diag_angle)]},
            ),
            Op("rect", {"length": _r3(diag_len), "width": s}),
            Op("extrude", {"distance": T}),
            # Diagonal from bottom-right to top-left
            Op(
                "union",
                {
                    "ops": _rect_rot_at(
                        cx=0.0,
                        cy=0.0,
                        length=diag_len,
                        width=s,
                        thickness=T,
                        angle_deg=-diag_angle,
                    ),
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "letter": "X", "ref": self.REF},
        )


# 12. simple_number_8_plate — figure 8 (two stacked annular rings)
class SimpleNumber8PlateFamily(BaseFamily):
    name = "simple_number_8_plate"
    standard = "N/A"
    REF = "imagined: digit '8' nameplate / signage character"

    def sample_params(self, difficulty, rng):
        # Outer disc radius (each lobe)
        r_out = round(float(rng.uniform(15, 28)), 1)
        stroke = round(r_out * float(rng.uniform(0.22, 0.32)), 1)
        thickness = round(float(rng.uniform(3, 12)), 1)
        return {
            "r_out": r_out,
            "stroke": stroke,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_out"] >= 10
            and 3 <= p["stroke"] < p["r_out"] * 0.45
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        ro = p["r_out"]
        s = p["stroke"]
        T = p["thickness"]
        ri = ro - s
        # Two outer discs stacked vertically (top center at +ro, bottom at -ro).
        # Then cut the inner discs to leave two annular rings sharing the
        # mid-stroke at y=0.
        ops = [
            # Top outer disc
            Op(
                "transformed",
                {"offset": [0, _r3(ro), 0], "rotate": [0, 0, 0]},
            ),
            Op("circle", {"radius": _r3(ro)}),
            Op("extrude", {"distance": _r3(T)}),
            # Bottom outer disc
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, _r3(-ro), 0],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "circle", "args": {"radius": _r3(ro)}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                    "plane": "XY",
                },
            ),
            # Cut top inner disc
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, _r3(ro), 0],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "circle", "args": {"radius": _r3(ri)}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                    "plane": "XY",
                },
            ),
            # Cut bottom inner disc
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, _r3(-ro), 0],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "circle", "args": {"radius": _r3(ri)}},
                        {"name": "extrude", "args": {"distance": _r3(T)}},
                    ],
                    "plane": "XY",
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "thin_plate": True,
                "letter": "8",
                "sketch_arc": True,
                "ref": self.REF,
            },
        )


ALL_FAMILIES = [
    SimpleLetterLPlateFamily,
    SimpleLetterTPlateFamily,
    SimpleLetterHPlateFamily,
    SimpleLetterEPlateFamily,
    SimpleLetterFPlateFamily,
    SimpleLetterPPlateFamily,
    SimpleLetterDPlateFamily,
    SimpleLetterUPlateFamily,
    SimpleLetterJPlateFamily,
    SimpleLetterYPlateFamily,
    SimpleLetterXPlateFamily,
    SimpleNumber8PlateFamily,
]
