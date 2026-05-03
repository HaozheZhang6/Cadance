"""simple_face_pack — enclosed-curve outline + internal cuts topology class.

Each family: closed 2D outer profile (circle/ellipse/rounded-rect/figure-8/
lock-shape/etc.) → extrude → workplane(>Z) → N internal cuts (cutThruAll
or cutBlind half-depth grooves).  Recognizable from a top-down view as a
specific symbol or device face (emoji, dial, target, die, phone back,
keypad, CD, eyeglasses, padlock).

Op vocabulary (verified against pipeline/builder.py):
  - circle, ellipse, rect, polyline, moveTo, lineTo, threePointArc, close
  - extrude, cutThruAll, cutBlind
  - workplane{">Z"}, center, pushPoints, polarArray, rarray
  - hole, slot2D

Family list:
  simple_face_emoji_plate         disc + 2 eye holes + arc-mouth (mood variants)
  simple_dial_plate               disc + N radial tick slot cuts (clock face)
  simple_perforated_disc_with_pattern  disc + ring of N holes + center bore
  simple_target_plate             disc + concentric blind annular grooves
  simple_die_face_plate           rounded square + N dot holes (die pattern 1..6)
  simple_cell_phone_back_plate    rounded rect + camera hole + speaker slot + button hole
  simple_keypad_button_plate      rounded rect + grid of small holes (3x4 / 4x4)
  simple_cd_disc                  disc + center bore + small offset pin holes
  simple_eyeglasses_plate         figure-8 outline (two circles + bridge) with through cuts
  simple_lock_plate               rounded rect + keyhole cutout (round + slot)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ---------- shared helpers --------------------------------------------------


def _r3(x):
    return round(float(x), 3)


def _round_pt(p):
    return (_r3(p[0]), _r3(p[1]))


def _arc_pt(cx, cy, r, a):
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def _rounded_rect_polyline(L, W, r, n_corner=8):
    """CCW closed polyline approximating a rounded rectangle.

    L = total length (x), W = total width (y), r = corner radius.
    Each corner is sampled with n_corner points along its quarter-arc.
    """
    hl, hw = L / 2.0, W / 2.0
    # Corner centers (CCW order starting bottom-right)
    corners = [
        (hl - r, -hw + r, -math.pi / 2, 0.0),  # bottom-right
        (hl - r, hw - r, 0.0, math.pi / 2),  # top-right
        (-hl + r, hw - r, math.pi / 2, math.pi),  # top-left
        (-hl + r, -hw + r, math.pi, 3 * math.pi / 2),  # bottom-left
    ]
    pts: list[tuple[float, float]] = []
    for cx, cy, a0, a1 in corners:
        for i in range(n_corner + 1):
            t = a0 + (a1 - a0) * i / n_corner
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


# ---------- families --------------------------------------------------------


# 1. simple_face_emoji_plate — disc + 2 eyes + arc mouth (3 moods via curvature)
class SimpleFaceEmojiPlateFamily(BaseFamily):
    name = "simple_face_emoji_plate"
    standard = "N/A"
    REF = "imagined: emoji medallion with 3 moods (happy/sad/neutral)"

    def sample_params(self, difficulty, rng):
        r_face = round(float(rng.uniform(25, 45)), 1)
        thickness = round(float(rng.uniform(4, 12)), 1)
        eye_r = round(r_face * float(rng.uniform(0.08, 0.13)), 1)
        eye_off_x = round(r_face * 0.35, 1)
        eye_off_y = round(r_face * 0.30, 1)
        mouth_r = round(r_face * float(rng.uniform(0.45, 0.60)), 1)
        mouth_w = round(eye_r * 1.1, 1)
        # mood: +1 happy (smile), -1 sad (frown), 0 neutral (straight slot)
        mood = int(rng.choice([1, -1, 0]))
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
            "mood": mood,
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
            and p["mood"] in (-1, 0, 1)
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
        mood = p["mood"]

        ops: list = [
            Op("circle", {"radius": rf}),
            Op("extrude", {"distance": T}),
            Op("workplane", {"selector": ">Z"}),
            Op("pushPoints", {"points": [(-ex, ey), (ex, ey)]}),
            Op("hole", {"diameter": 2 * er}),
            Op("workplane", {"selector": ">Z"}),
        ]

        if mood == 0:
            # Neutral: a straight horizontal slot mouth.
            ops += [
                Op("center", {"x": _r3(0.0), "y": _r3(my)}),
                Op(
                    "slot2D",
                    {
                        "length": _r3(mr * 1.6),
                        "width": _r3(mw),
                        "angle": 0,
                    },
                ),
                Op("cutThruAll", {}),
            ]
        else:
            # Smile (mood=+1) or frown (mood=-1) arc-bar mouth.
            # Smile: arc opens DOWN from center (corners up). Frown: arc opens UP.
            ro = mr + mw / 2.0
            ri = mr - mw / 2.0
            sweep_half = math.radians(55)
            cx = 0.0
            cy = my
            if mood == 1:
                # Smile: center BELOW arc, arc passes through lowest point at -π/2.
                am = -math.pi / 2
            else:
                # Frown: center ABOVE arc, arc passes through highest point at +π/2.
                # Shift mouth center UP to keep it inside the face.
                cy = -my  # flip y position upward
                am = +math.pi / 2
            a0 = am - sweep_half
            a1 = am + sweep_half
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
                "emoji": True,
                "mood": ["sad", "neutral", "happy"][mood + 1],
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 2. simple_dial_plate — disc + N radial tick slot cuts (clock face)
class SimpleDialPlateFamily(BaseFamily):
    name = "simple_dial_plate"
    standard = "N/A"
    REF = "imagined: clock-face dial / instrument bezel with tick marks"

    def sample_params(self, difficulty, rng):
        r_face = round(float(rng.uniform(25, 50)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        n_ticks = int(rng.choice([4, 6, 8, 12]))
        tick_len = round(r_face * float(rng.uniform(0.15, 0.25)), 1)
        tick_w = round(r_face * float(rng.uniform(0.04, 0.08)), 1)
        tick_pcd = round(r_face - tick_len * 0.6, 1)
        center_hole_d = round(r_face * float(rng.uniform(0.10, 0.18)), 1)
        return {
            "r_face": r_face,
            "thickness": thickness,
            "n_ticks": n_ticks,
            "tick_len": tick_len,
            "tick_w": tick_w,
            "tick_pcd": tick_pcd,
            "center_hole_d": center_hole_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_face"] >= 18
            and p["thickness"] >= 1.5
            and p["n_ticks"] in (4, 6, 8, 12)
            and p["tick_len"] >= 3
            and p["tick_w"] >= 1.5
            and p["tick_pcd"] > p["tick_len"] / 2 + 2
            and p["tick_pcd"] < p["r_face"] - 1
            and p["center_hole_d"] >= 2
            and p["center_hole_d"] < p["r_face"] * 0.4
        )

    def make_program(self, p):
        rf = p["r_face"]
        T = p["thickness"]
        n = p["n_ticks"]
        tl = p["tick_len"]
        tw = p["tick_w"]
        pcd = p["tick_pcd"]
        ch = p["center_hole_d"]
        ops = [
            Op("circle", {"radius": rf}),
            Op("extrude", {"distance": T}),
            # Center hole
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": ch}),
            # Polar array of radial slot ticks
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": pcd,
                    "startAngle": 0,
                    "angle": 360,
                    "count": n,
                },
            ),
            # slot2D length=tl (radial), width=tw (tangential), angle=0 means
            # the polarArray automatically rotates each instance to align with
            # the radial direction (length axis).
            Op("slot2D", {"length": tl, "width": tw, "angle": 0}),
            Op("cutThruAll", {}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "dial": True,
                "polar_array": n,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 3. simple_perforated_disc_with_pattern — disc + ring of N holes + center bore
class SimplePerforatedDiscWithPatternFamily(BaseFamily):
    name = "simple_perforated_disc_with_pattern"
    standard = "N/A"
    REF = "imagined: speaker grille / vent disc with polar hole pattern"

    def sample_params(self, difficulty, rng):
        r_face = round(float(rng.uniform(25, 50)), 1)
        thickness = round(float(rng.uniform(3, 10)), 1)
        n_holes = int(rng.choice([4, 6, 8, 12]))
        hole_d = round(r_face * float(rng.uniform(0.10, 0.18)), 1)
        ring_pcd = round(r_face * float(rng.uniform(0.55, 0.72)), 1)
        center_d = round(r_face * float(rng.uniform(0.15, 0.25)), 1)
        return {
            "r_face": r_face,
            "thickness": thickness,
            "n_holes": n_holes,
            "hole_d": hole_d,
            "ring_pcd": ring_pcd,
            "center_d": center_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        # Tangential clearance between adjacent holes on the ring
        circ = 2 * math.pi * p["ring_pcd"] / p["n_holes"]
        return (
            p["r_face"] >= 18
            and p["thickness"] >= 1.5
            and p["n_holes"] in (4, 6, 8, 12)
            and p["hole_d"] >= 2
            and p["hole_d"] < circ * 0.7
            and p["ring_pcd"] + p["hole_d"] / 2 < p["r_face"] - 2
            and p["ring_pcd"] - p["hole_d"] / 2 > p["center_d"] / 2 + 2
            and p["center_d"] >= 2
        )

    def make_program(self, p):
        rf = p["r_face"]
        T = p["thickness"]
        ops = [
            Op("circle", {"radius": rf}),
            Op("extrude", {"distance": T}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["center_d"]}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": p["ring_pcd"],
                    "startAngle": 0,
                    "angle": 360,
                    "count": p["n_holes"],
                },
            ),
            Op("hole", {"diameter": p["hole_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "perforated": True,
                "polar_array": p["n_holes"],
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 4. simple_target_plate — disc + concentric blind annular grooves (bullseye)
class SimpleTargetPlateFamily(BaseFamily):
    name = "simple_target_plate"
    standard = "N/A"
    REF = "imagined: archery target / bullseye plate with concentric grooves"

    def sample_params(self, difficulty, rng):
        r_face = round(float(rng.uniform(30, 50)), 1)
        thickness = round(float(rng.uniform(5, 12)), 1)
        n_rings = int(rng.choice([2, 3, 4]))
        groove_w = round(r_face * float(rng.uniform(0.04, 0.08)), 1)
        groove_depth = round(thickness * float(rng.uniform(0.25, 0.45)), 1)
        return {
            "r_face": r_face,
            "thickness": thickness,
            "n_rings": n_rings,
            "groove_w": groove_w,
            "groove_depth": groove_depth,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_face"] >= 20
            and p["thickness"] >= 3
            and p["n_rings"] in (2, 3, 4)
            and p["groove_w"] >= 1.5
            and p["groove_depth"] > 0
            and p["groove_depth"] < p["thickness"] - 1
            and p["r_face"] / (p["n_rings"] + 1) > p["groove_w"] * 2
        )

    def make_program(self, p):
        rf = p["r_face"]
        T = p["thickness"]
        n = p["n_rings"]
        gw = p["groove_w"]
        gd = p["groove_depth"]
        # Ring radii spaced evenly between the center and edge.
        # Inner ring at rf*0.25, outer at rf*0.85.
        r_inner = rf * 0.25
        r_outer = rf * 0.85
        ops = [
            Op("circle", {"radius": rf}),
            Op("extrude", {"distance": T}),
        ]
        for i in range(n):
            t = i / max(1, n - 1) if n > 1 else 0.5
            r_mean = r_inner + (r_outer - r_inner) * t
            ro = r_mean + gw / 2.0
            ri = r_mean - gw / 2.0
            # Annular groove sketch on top face: outer circle minus inner circle.
            # Build with two circles sketched at once on the same workplane —
            # CadQuery will treat them as a single sketch with hole.
            ops += [
                Op("workplane", {"selector": ">Z"}),
                Op("circle", {"radius": _r3(ro)}),
                Op("circle", {"radius": _r3(ri)}),
                Op("cutBlind", {"depth": gd}),
            ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "target": True,
                "n_rings": n,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 5. simple_die_face_plate — rounded square + dot holes in die pattern (1..6)
class SimpleDieFacePlateFamily(BaseFamily):
    name = "simple_die_face_plate"
    standard = "N/A"
    REF = "imagined: single face of a six-sided die with N pip holes"

    # Die pip layout normalized to a unit square [-1, 1]^2
    _PIPS = {
        1: [(0, 0)],
        2: [(-0.5, 0.5), (0.5, -0.5)],
        3: [(-0.5, 0.5), (0, 0), (0.5, -0.5)],
        4: [(-0.5, 0.5), (0.5, 0.5), (-0.5, -0.5), (0.5, -0.5)],
        5: [
            (-0.5, 0.5),
            (0.5, 0.5),
            (0, 0),
            (-0.5, -0.5),
            (0.5, -0.5),
        ],
        6: [
            (-0.5, 0.5),
            (0.5, 0.5),
            (-0.5, 0),
            (0.5, 0),
            (-0.5, -0.5),
            (0.5, -0.5),
        ],
    }

    def sample_params(self, difficulty, rng):
        side = round(float(rng.uniform(30, 50)), 1)
        thickness = round(float(rng.uniform(5, 14)), 1)
        corner_r = round(side * float(rng.uniform(0.08, 0.15)), 1)
        n_pips = int(rng.choice([1, 2, 3, 4, 5, 6]))
        pip_d = round(side * float(rng.uniform(0.10, 0.16)), 1)
        return {
            "side": side,
            "thickness": thickness,
            "corner_r": corner_r,
            "n_pips": n_pips,
            "pip_d": pip_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["side"] >= 20
            and p["thickness"] >= 3
            and p["corner_r"] >= 1
            and p["corner_r"] < p["side"] * 0.3
            and p["n_pips"] in (1, 2, 3, 4, 5, 6)
            and p["pip_d"] >= 2
            and p["pip_d"] < p["side"] * 0.25
        )

    def make_program(self, p):
        s = p["side"]
        T = p["thickness"]
        cr = p["corner_r"]
        n = p["n_pips"]
        pd = p["pip_d"]
        # Outer rounded-square outline as polyline
        outline = _rounded_rect_polyline(s, s, cr, n_corner=8)
        outline = [_round_pt(pt) for pt in outline]
        # Pip positions: scale unit-square positions by side*0.35 (so pips sit
        # comfortably inside the corner radius).
        scale = s * 0.35
        pip_pts = [(scale * x, scale * y) for x, y in self._PIPS[n]]
        pip_pts = [_round_pt(pt) for pt in pip_pts]
        ops = [
            Op("polyline", {"points": outline}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
            Op("workplane", {"selector": ">Z"}),
            Op("pushPoints", {"points": pip_pts}),
            Op("hole", {"diameter": pd}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "die_face": True,
                "n_pips": n,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 6. simple_cell_phone_back_plate — rounded rect + camera hole + speaker slot + button
class SimpleCellPhoneBackPlateFamily(BaseFamily):
    name = "simple_cell_phone_back_plate"
    standard = "N/A"
    REF = "imagined: phone back panel with camera lens, speaker slot, button"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(80, 130)), 1)
        W = round(float(rng.uniform(45, 70)), 1)
        T = round(float(rng.uniform(3, 8)), 1)
        cr = round(W * float(rng.uniform(0.10, 0.18)), 1)
        cam_d = round(W * float(rng.uniform(0.18, 0.28)), 1)
        # camera at upper-left quadrant
        cam_x = -L * 0.30
        cam_y = +W * 0.28
        speaker_l = round(W * float(rng.uniform(0.22, 0.32)), 1)
        speaker_w = round(W * float(rng.uniform(0.05, 0.09)), 1)
        # speaker centered, near top
        speaker_x = 0.0
        speaker_y = +W * 0.40
        button_d = round(W * float(rng.uniform(0.05, 0.09)), 1)
        # button on right side, lower-right
        button_x = +L * 0.35
        button_y = -W * 0.25
        return {
            "length": L,
            "width": W,
            "thickness": T,
            "corner_r": cr,
            "cam_d": cam_d,
            "cam_x": round(cam_x, 1),
            "cam_y": round(cam_y, 1),
            "speaker_l": speaker_l,
            "speaker_w": speaker_w,
            "speaker_x": speaker_x,
            "speaker_y": round(speaker_y, 1),
            "button_d": button_d,
            "button_x": round(button_x, 1),
            "button_y": round(button_y, 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] >= 60
            and p["width"] >= 30
            and p["thickness"] >= 2
            and p["corner_r"] >= 2
            and p["corner_r"] < p["width"] * 0.4
            and p["cam_d"] >= 4
            and p["cam_d"] < p["width"] * 0.4
            and p["speaker_l"] >= 6
            and p["speaker_w"] >= 2
            and p["speaker_w"] < p["speaker_l"]
            and p["button_d"] >= 2
        )

    def make_program(self, p):
        L = p["length"]
        W = p["width"]
        T = p["thickness"]
        cr = p["corner_r"]
        outline = _rounded_rect_polyline(L, W, cr, n_corner=8)
        outline = [_round_pt(pt) for pt in outline]
        ops = [
            Op("polyline", {"points": outline}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
            # Camera hole
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": _r3(p["cam_x"]), "y": _r3(p["cam_y"])}),
            Op("hole", {"diameter": p["cam_d"]}),
            # Speaker slot
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": _r3(p["speaker_x"]), "y": _r3(p["speaker_y"])}),
            Op(
                "slot2D",
                {
                    "length": p["speaker_l"],
                    "width": p["speaker_w"],
                    "angle": 0,
                },
            ),
            Op("cutThruAll", {}),
            # Button hole
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": _r3(p["button_x"]), "y": _r3(p["button_y"])}),
            Op("hole", {"diameter": p["button_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "phone_back": True,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 7. simple_keypad_button_plate — rounded rect + grid of small holes
class SimpleKeypadButtonPlateFamily(BaseFamily):
    name = "simple_keypad_button_plate"
    standard = "N/A"
    REF = "imagined: numeric keypad face plate with grid of button holes"

    def sample_params(self, difficulty, rng):
        # Pick layout: 3x4 (numeric keypad) or 4x4 (hex/full)
        layout = str(rng.choice(["3x4", "4x4"]))
        nx, ny = (3, 4) if layout == "3x4" else (4, 4)
        # Cell pitch
        pitch = round(float(rng.uniform(12, 18)), 1)
        margin = round(pitch * 0.6, 1)
        L = round(nx * pitch + 2 * margin, 1)
        W = round(ny * pitch + 2 * margin, 1)
        T = round(float(rng.uniform(3, 8)), 1)
        cr = round(margin * 0.6, 1)
        hole_d = round(pitch * float(rng.uniform(0.45, 0.65)), 1)
        return {
            "layout": layout,
            "n_x": nx,
            "n_y": ny,
            "pitch": pitch,
            "length": L,
            "width": W,
            "thickness": T,
            "corner_r": cr,
            "hole_d": hole_d,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["layout"] in ("3x4", "4x4")
            and p["pitch"] >= 8
            and p["thickness"] >= 1.5
            and p["hole_d"] >= 3
            and p["hole_d"] < p["pitch"] - 2
            and p["corner_r"] >= 1
        )

    def make_program(self, p):
        L, W, T = p["length"], p["width"], p["thickness"]
        cr = p["corner_r"]
        outline = _rounded_rect_polyline(L, W, cr, n_corner=8)
        outline = [_round_pt(pt) for pt in outline]
        ops = [
            Op("polyline", {"points": outline}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "rarray",
                {
                    "xSpacing": p["pitch"],
                    "ySpacing": p["pitch"],
                    "xCount": p["n_x"],
                    "yCount": p["n_y"],
                },
            ),
            Op("hole", {"diameter": p["hole_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "keypad": True,
                "rarray": (p["n_x"], p["n_y"]),
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 8. simple_cd_disc — disc + center bore + small offset pin holes
class SimpleCdDiscFamily(BaseFamily):
    name = "simple_cd_disc"
    standard = "N/A"
    REF = "imagined: optical CD/DVD disc — outer disc + 15mm center bore"

    def sample_params(self, difficulty, rng):
        r_outer = round(float(rng.uniform(50, 60)), 1)  # CD-like ~60mm
        thickness = round(float(rng.uniform(1.2, 2.5)), 2)
        bore_d = round(float(rng.uniform(14.0, 16.0)), 1)  # CD bore = 15mm
        n_pins = int(rng.choice([3, 4, 6]))
        pin_d = round(float(rng.uniform(1.5, 2.5)), 1)
        # pin holes lie in a small ring around the bore (just outside it)
        pin_pcd = round(bore_d * 0.5 + pin_d * 1.2 + bore_d * 0.5, 2)
        # bore radius = bore_d/2; pin centers at radius slightly > bore_d/2 + pin_d
        pin_pcd = round(bore_d / 2.0 + pin_d, 2)
        return {
            "r_outer": r_outer,
            "thickness": thickness,
            "bore_d": bore_d,
            "n_pins": n_pins,
            "pin_d": pin_d,
            "pin_pcd": pin_pcd,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["r_outer"] >= 30
            and p["thickness"] >= 0.8
            and p["bore_d"] >= 8
            and p["bore_d"] < p["r_outer"]
            and p["n_pins"] in (3, 4, 6)
            and p["pin_d"] >= 1.0
            and p["pin_pcd"] > p["bore_d"] / 2 + p["pin_d"] / 2
            and p["pin_pcd"] + p["pin_d"] / 2 < p["r_outer"] - 2
        )

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_outer"]}),
            Op("extrude", {"distance": p["thickness"]}),
            Op("workplane", {"selector": ">Z"}),
            Op("hole", {"diameter": p["bore_d"]}),
            Op("workplane", {"selector": ">Z"}),
            Op(
                "polarArray",
                {
                    "radius": p["pin_pcd"],
                    "startAngle": 0,
                    "angle": 360,
                    "count": p["n_pins"],
                },
            ),
            Op("hole", {"diameter": p["pin_d"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "cd_disc": True,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 9. simple_eyeglasses_plate — figure-8 outline (two circles + bridge), open lenses
class SimpleEyeglassesPlateFamily(BaseFamily):
    name = "simple_eyeglasses_plate"
    standard = "N/A"
    REF = "imagined: eyeglasses front frame — two circular lenses + bridge"

    def sample_params(self, difficulty, rng):
        lens_r = round(float(rng.uniform(15, 25)), 1)
        bridge = round(lens_r * float(rng.uniform(0.40, 0.65)), 1)
        rim = round(lens_r * float(rng.uniform(0.18, 0.28)), 1)
        thickness = round(float(rng.uniform(2, 5)), 1)
        return {
            "lens_r": lens_r,
            "bridge": bridge,
            "rim": rim,
            "thickness": thickness,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["lens_r"] >= 10
            and p["bridge"] >= 4
            and p["rim"] >= 2
            and p["rim"] < p["lens_r"] * 0.5
            and p["thickness"] >= 1.5
        )

    def make_program(self, p):
        # Outer profile: two outer circles (radius lens_r + rim) at ±cx,
        # connected naturally where they overlap (bridge). To keep this as
        # a sketch-first single extrude, we sketch: two outer circles +
        # a connecting rectangle (the bridge bar), then subtract two inner
        # circles (the lens openings) all in one workplane sketch.
        lr = p["lens_r"]
        rim = p["rim"]
        br = p["bridge"]
        T = p["thickness"]
        # Lens outer radius
        ro = lr + rim
        # Distance between lens centers: must be > 2*ro - bridge_overlap so that
        # the two outer circles remain connected only via the bridge bar.
        # Choose: cx = ro + br/2 + rim*0.3 so circles don't overlap directly.
        cx = ro + br / 2.0 + rim * 0.5
        # Bridge bar: horizontal rect spanning between the two outer circles
        # at y=0, length = 2*cx (full span), width = rim*1.2 (bar height).
        bar_l = 2 * cx
        bar_w = rim * 1.2
        ops = [
            # Two outer lens-rim discs
            Op("center", {"x": _r3(-cx), "y": _r3(0)}),
            Op("circle", {"radius": _r3(ro)}),
            Op("center", {"x": _r3(2 * cx), "y": _r3(0)}),
            Op("circle", {"radius": _r3(ro)}),
            # Reset center, draw bridge bar
            Op("center", {"x": _r3(-cx), "y": _r3(0)}),
            Op("rect", {"length": _r3(bar_l), "width": _r3(bar_w)}),
            Op("extrude", {"distance": T}),
            # Cut two lens openings
            Op("workplane", {"selector": ">Z"}),
            Op(
                "pushPoints",
                {"points": [(_r3(-cx), 0.0), (_r3(cx), 0.0)]},
            ),
            Op("hole", {"diameter": 2 * lr}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={
                "eyeglasses": True,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


# 10. simple_lock_plate — rounded rect + keyhole cutout (round + slot below)
class SimpleLockPlateFamily(BaseFamily):
    name = "simple_lock_plate"
    standard = "N/A"
    REF = "imagined: padlock face plate with keyhole (round + drop slot)"

    def sample_params(self, difficulty, rng):
        L = round(float(rng.uniform(40, 70)), 1)
        W = round(float(rng.uniform(30, 55)), 1)
        T = round(float(rng.uniform(4, 10)), 1)
        cr = round(min(L, W) * float(rng.uniform(0.10, 0.18)), 1)
        # Keyhole: round opening + narrow drop slot. Place slightly above center.
        kh_d = round(min(L, W) * float(rng.uniform(0.18, 0.28)), 1)
        kh_y = round(W * 0.10, 1)  # circle center above plate centroid
        slot_drop = round(kh_d * float(rng.uniform(1.3, 2.0)), 1)
        slot_w = round(kh_d * float(rng.uniform(0.30, 0.45)), 1)
        return {
            "length": L,
            "width": W,
            "thickness": T,
            "corner_r": cr,
            "kh_d": kh_d,
            "kh_y": kh_y,
            "slot_drop": slot_drop,
            "slot_w": slot_w,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["length"] >= 30
            and p["width"] >= 25
            and p["thickness"] >= 2
            and p["corner_r"] >= 2
            and p["corner_r"] < min(p["length"], p["width"]) * 0.4
            and p["kh_d"] >= 4
            and p["slot_drop"] >= 4
            and p["slot_w"] >= 1.5
            and p["slot_w"] < p["kh_d"]
            and p["kh_y"] + p["kh_d"] / 2 < p["width"] / 2 - 2
            and p["kh_y"] - p["slot_drop"] - p["slot_w"] / 2 > -p["width"] / 2 + 2
        )

    def make_program(self, p):
        L, W, T = p["length"], p["width"], p["thickness"]
        cr = p["corner_r"]
        outline = _rounded_rect_polyline(L, W, cr, n_corner=8)
        outline = [_round_pt(pt) for pt in outline]
        kh_y = p["kh_y"]
        slot_drop = p["slot_drop"]
        # Slot center sits halfway between circle center and slot bottom.
        slot_center_y = kh_y - slot_drop / 2.0
        ops = [
            Op("polyline", {"points": outline}),
            Op("close", {}),
            Op("extrude", {"distance": T}),
            # Round part of keyhole
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": _r3(0), "y": _r3(kh_y)}),
            Op("hole", {"diameter": p["kh_d"]}),
            # Drop slot below
            Op("workplane", {"selector": ">Z"}),
            Op("center", {"x": _r3(0), "y": _r3(slot_center_y)}),
            Op(
                "slot2D",
                {
                    "length": _r3(slot_drop),
                    "width": _r3(p["slot_w"]),
                    "angle": 90,
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
                "lock_face": True,
                "keyhole": True,
                "thin_plate": True,
                "ref": self.REF,
            },
        )


ALL_FAMILIES = [
    SimpleFaceEmojiPlateFamily,
    SimpleDialPlateFamily,
    SimplePerforatedDiscWithPatternFamily,
    SimpleTargetPlateFamily,
    SimpleDieFacePlateFamily,
    SimpleCellPhoneBackPlateFamily,
    SimpleKeypadButtonPlateFamily,
    SimpleCdDiscFamily,
    SimpleEyeglassesPlateFamily,
    SimpleLockPlateFamily,
]
