"""simple_sheet_sections_pack — 13 sheet metal cross-section families.

Reference: F360 sheet metal samples + DIN/AISC standard structural sections.
All built as polyline cross-section + extrude (薄板 sketch-first).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


def _emit(self, p, pts, tags=None):
    pts_r = [(round(x, 3), round(y, 3)) for x, y in pts]
    ops = [Op("moveTo", {"x": pts_r[0][0], "y": pts_r[0][1]})]
    for x, y in pts_r[1:]:
        ops.append(Op("lineTo", {"x": x, "y": y}))
    ops += [Op("close", {}), Op("extrude", {"distance": p["length"]})]
    return Program(
        family=self.name,
        difficulty=p["difficulty"],
        params=p,
        ops=ops,
        feature_tags={**({"thin_plate": True, "ref": self.REF}), **(tags or {})},
    )


# 1. simple_c_channel — C-section
class SimpleCChannelFamily(BaseFamily):
    name = "simple_c_channel"
    standard = "N/A"
    REF = "imagined: C-channel sheet metal"

    def sample_params(self, difficulty, rng):
        return {
            "outer_w": round(float(rng.uniform(30, 60)), 1),
            "outer_h": round(float(rng.uniform(40, 80)), 1),
            "thickness_2d": round(float(rng.uniform(2, 5)), 1),
            "length": round(float(rng.uniform(30, 80)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["thickness_2d"] * 4 < min(p["outer_w"], p["outer_h"])

    def make_program(self, p):
        W = p["outer_w"]
        H = p["outer_h"]
        t = p["thickness_2d"]
        pts = [
            (0, 0),
            (W, 0),
            (W, t),
            (t, t),
            (t, H - t),
            (W, H - t),
            (W, H),
            (0, H),
        ]
        return _emit(self, p, pts)


# 2. simple_u_channel_simple — U-shaped sheet
class SimpleUChannelSimpleFamily(BaseFamily):
    name = "simple_u_channel_simple"
    standard = "N/A"
    REF = "imagined: U-channel struct"

    def sample_params(self, difficulty, rng):
        return {
            "outer_w": round(float(rng.uniform(40, 70)), 1),
            "outer_h": round(float(rng.uniform(20, 50)), 1),
            "thickness_2d": round(float(rng.uniform(2, 6)), 1),
            "length": round(float(rng.uniform(40, 100)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["thickness_2d"] * 4 < min(p["outer_w"], p["outer_h"])

    def make_program(self, p):
        W = p["outer_w"]
        H = p["outer_h"]
        t = p["thickness_2d"]
        pts = [
            (0, 0),
            (W, 0),
            (W, H),
            (W - t, H),
            (W - t, t),
            (t, t),
            (t, H),
            (0, H),
        ]
        return _emit(self, p, pts)


# 3. simple_hat_section — Top-hat 帽形
class SimpleHatSectionFamily(BaseFamily):
    name = "simple_hat_section"
    standard = "N/A"
    REF = "imagined: top-hat profile / lab support"

    def sample_params(self, difficulty, rng):
        return {
            "brim_w": round(float(rng.uniform(50, 80)), 1),
            "crown_w": round(float(rng.uniform(20, 40)), 1),
            "crown_h": round(float(rng.uniform(15, 30)), 1),
            "brim_t": round(float(rng.uniform(3, 6)), 1),
            "length": round(float(rng.uniform(40, 100)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["crown_w"] + 8 < p["brim_w"]

    def make_program(self, p):
        bw = p["brim_w"]
        cw = p["crown_w"]
        ch = p["crown_h"]
        t = p["brim_t"]
        side = (bw - cw) / 2
        pts = [
            (0, 0),
            (bw, 0),
            (bw, t),
            (bw - side + t, t),
            (bw - side + t, ch),
            (side - t, ch),
            (side - t, t),
            (0, t),
        ]
        return _emit(self, p, pts)


# 4. simple_z_section_struct (Z structural shape — different from simple_z_section_plate which is symmetric)
class SimpleZSectionStructFamily(BaseFamily):
    name = "simple_z_section_struct"
    standard = "N/A"
    REF = "imagined: Z-purlin / Z-section beam"

    def sample_params(self, difficulty, rng):
        return {
            "flange_w": round(float(rng.uniform(25, 50)), 1),
            "web_h": round(float(rng.uniform(40, 80)), 1),
            "thickness_2d": round(float(rng.uniform(2, 5)), 1),
            "length": round(float(rng.uniform(40, 100)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["thickness_2d"] * 4 < p["flange_w"]

    def make_program(self, p):
        fw = p["flange_w"]
        H = p["web_h"]
        t = p["thickness_2d"]
        # bottom flange goes left, top flange goes right
        pts = [
            (-fw, 0),
            (0, 0),
            (0, H - t),
            (fw, H - t),
            (fw, H),
            (-fw + t, H),
            (-fw + t, t),
            (-fw, t),
        ]
        # ensure CCW closed
        return _emit(self, p, pts)


# 5. simple_i_beam_simple — symmetric I cross section
class SimpleIBeamSimpleFamily(BaseFamily):
    name = "simple_i_beam_simple"
    standard = "N/A"
    REF = "imagined: simplified I-beam"

    def sample_params(self, difficulty, rng):
        return {
            "flange_w": round(float(rng.uniform(40, 70)), 1),
            "height": round(float(rng.uniform(50, 100)), 1),
            "flange_t": round(float(rng.uniform(4, 8)), 1),
            "web_t": round(float(rng.uniform(3, 6)), 1),
            "length": round(float(rng.uniform(40, 100)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["web_t"] + 4 < p["flange_w"] and p["flange_t"] * 2 + 4 < p["height"]

    def make_program(self, p):
        W = p["flange_w"]
        H = p["height"]
        ft = p["flange_t"]
        wt = p["web_t"]
        pts = [
            (-W / 2, -H / 2),
            (W / 2, -H / 2),
            (W / 2, -H / 2 + ft),
            (wt / 2, -H / 2 + ft),
            (wt / 2, H / 2 - ft),
            (W / 2, H / 2 - ft),
            (W / 2, H / 2),
            (-W / 2, H / 2),
            (-W / 2, H / 2 - ft),
            (-wt / 2, H / 2 - ft),
            (-wt / 2, -H / 2 + ft),
            (-W / 2, -H / 2 + ft),
        ]
        return _emit(self, p, pts)


# 6. simple_angle_bracket_90
class SimpleAngleBracket90Family(BaseFamily):
    name = "simple_angle_bracket_90"
    standard = "N/A"
    REF = "imagined: 90° angle iron"

    def sample_params(self, difficulty, rng):
        a = round(float(rng.uniform(30, 60)), 1)
        return {
            "arm": a,
            "thickness_2d": round(float(rng.uniform(3, 7)), 1),
            "length": round(float(rng.uniform(50, 120)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["arm"] > p["thickness_2d"] * 3

    def make_program(self, p):
        a = p["arm"]
        t = p["thickness_2d"]
        pts = [(0, 0), (a, 0), (a, t), (t, t), (t, a), (0, a)]
        return _emit(self, p, pts)


# 7. simple_angle_bracket_135 (obtuse angle bar)
class SimpleAngleBracket135Family(BaseFamily):
    name = "simple_angle_bracket_135"
    standard = "N/A"
    REF = "imagined: 135° obtuse angle bar"

    def sample_params(self, difficulty, rng):
        return {
            "arm": round(float(rng.uniform(30, 60)), 1),
            "thickness_2d": round(float(rng.uniform(3, 7)), 1),
            "length": round(float(rng.uniform(50, 120)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["arm"] > p["thickness_2d"] * 3

    def make_program(self, p):
        import math

        a = p["arm"]
        t = p["thickness_2d"]
        ang = math.radians(135)
        a * math.cos(ang)
        a * math.sin(ang)
        # outer L: (0,0)→(a,0)→(a,t)→(t,t)→(t+cx*0,...) — simplified: just use 90 rotated
        # Simpler: approximate with two arms at 135° between them
        # Inner corner at origin, arm1 along +x, arm2 at 135°
        ux1, _uy1 = 1, 0  # arm1 direction
        ux2, uy2 = math.cos(ang), math.sin(ang)  # arm2 direction
        # perpendicular (inward) of arm1: (0, 1)
        # perpendicular (inward) of arm2: (-sin(ang), cos(ang))
        # outer corners
        (a * ux1 + 0 * t, 0)  # arm1 tip, outer side (y=0)
        (a * ux1, t)  # arm1 tip, inner side
        (a * ux2, a * uy2)
        # inner corner: intersection of two thickness offsets
        # Use simplified flat polyline
        pts = [
            (a * ux1, 0),
            (a * ux1, t),
            (t * ux1, t),
            (t * ux2, t * uy2),
            (a * ux2 + t * (-uy2), a * uy2 + t * ux2),
            (a * ux2, a * uy2),
        ]
        return _emit(self, p, pts)


# 8. simple_box_section (closed rectangular tube)
class SimpleBoxSectionFamily(BaseFamily):
    name = "simple_box_section"
    standard = "N/A"
    REF = "imagined: rectangular hollow tube / RHS"

    def sample_params(self, difficulty, rng):
        return {
            "outer_w": round(float(rng.uniform(30, 60)), 1),
            "outer_h": round(float(rng.uniform(20, 50)), 1),
            "thickness_2d": round(float(rng.uniform(2, 5)), 1),
            "length": round(float(rng.uniform(40, 120)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["thickness_2d"] * 4 < min(p["outer_w"], p["outer_h"])

    def make_program(self, p):
        W = p["outer_w"]
        H = p["outer_h"]
        t = p["thickness_2d"]
        ops = [
            Op("rect", {"length": W, "width": H}),
            Op("rect", {"length": W - 2 * t, "width": H - 2 * t}),
            Op("extrude", {"distance": p["length"]}),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"thin_plate": True, "hollow": True, "ref": self.REF},
        )


# 9. simple_unistrut (square tube with longitudinal slot)
class SimpleUnistrutFamily(BaseFamily):
    name = "simple_unistrut"
    standard = "N/A"
    REF = "imagined: Unistrut / strut channel"

    def sample_params(self, difficulty, rng):
        return {
            "outer_w": round(float(rng.uniform(35, 50)), 1),
            "outer_h": round(float(rng.uniform(35, 50)), 1),
            "slot_w": round(float(rng.uniform(8, 16)), 1),
            "thickness_2d": round(float(rng.uniform(2, 4)), 1),
            "length": round(float(rng.uniform(60, 120)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["slot_w"] + p["thickness_2d"] * 4 < p["outer_w"]

    def make_program(self, p):
        W = p["outer_w"]
        H = p["outer_h"]
        t = p["thickness_2d"]
        sw = p["slot_w"]
        # Box section with top slot
        pts = [
            (-W / 2, -H / 2),
            (W / 2, -H / 2),
            (W / 2, H / 2),
            (sw / 2, H / 2),
            (sw / 2, H / 2 - t),
            (W / 2 - t, H / 2 - t),
            (W / 2 - t, -H / 2 + t),
            (-W / 2 + t, -H / 2 + t),
            (-W / 2 + t, H / 2 - t),
            (-sw / 2, H / 2 - t),
            (-sw / 2, H / 2),
            (-W / 2, H / 2),
        ]
        return _emit(self, p, pts)


# 10. simple_top_hat_section — a different shape from hat_section: stepped top
class SimpleTopHatSectionFamily(BaseFamily):
    name = "simple_top_hat_section"
    standard = "N/A"
    REF = "imagined: top-hat with stepped crown"

    def sample_params(self, difficulty, rng):
        return {
            "brim_w": round(float(rng.uniform(60, 90)), 1),
            "mid_w": round(float(rng.uniform(35, 55)), 1),
            "crown_w": round(float(rng.uniform(15, 28)), 1),
            "step_h": round(float(rng.uniform(8, 18)), 1),
            "crown_h": round(float(rng.uniform(15, 28)), 1),
            "brim_t": round(float(rng.uniform(3, 6)), 1),
            "length": round(float(rng.uniform(40, 100)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["crown_w"] + 4 < p["mid_w"] and p["mid_w"] + 4 < p["brim_w"]

    def make_program(self, p):
        bw = p["brim_w"]
        mw = p["mid_w"]
        cw = p["crown_w"]
        sh = p["step_h"]
        ch = p["crown_h"]
        t = p["brim_t"]
        # stepped polyline
        pts = [
            (-bw / 2, 0),
            (bw / 2, 0),
            (bw / 2, t),
            (mw / 2, t),
            (mw / 2, sh),
            (cw / 2, sh),
            (cw / 2, sh + ch),
            (-cw / 2, sh + ch),
            (-cw / 2, sh),
            (-mw / 2, sh),
            (-mw / 2, t),
            (-bw / 2, t),
        ]
        return _emit(self, p, pts)


# 11. simple_l_section_thin — thin L-shape (different from simple_l_solid: longer, thinner)
class SimpleLSectionThinFamily(BaseFamily):
    name = "simple_l_section_thin"
    standard = "N/A"
    REF = "f360:angle iron / aluminum extrusion"

    def sample_params(self, difficulty, rng):
        return {
            "arm_h": round(float(rng.uniform(30, 60)), 1),
            "arm_v": round(float(rng.uniform(30, 60)), 1),
            "thickness_2d": round(float(rng.uniform(2, 5)), 1),
            "length": round(float(rng.uniform(60, 120)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["thickness_2d"] * 3 < min(p["arm_h"], p["arm_v"])

    def make_program(self, p):
        ah = p["arm_h"]
        av = p["arm_v"]
        t = p["thickness_2d"]
        pts = [(0, 0), (ah, 0), (ah, t), (t, t), (t, av), (0, av)]
        return _emit(self, p, pts)


# 12. simple_split_tube (cylinder with longitudinal slit)
class SimpleSplitTubeFamily(BaseFamily):
    name = "simple_split_tube"
    standard = "N/A"
    REF = "imagined: clamping sleeve / split tube"

    def sample_params(self, difficulty, rng):
        ro = round(float(rng.uniform(15, 30)), 1)
        return {
            "r_outer": ro,
            "r_inner": round(ro * float(rng.uniform(0.6, 0.85)), 1),
            "slit_w": round(float(rng.uniform(2, 5)), 1),
            "length": round(float(rng.uniform(30, 80)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["r_outer"] > p["r_inner"] + 1.5

    def make_program(self, p):
        ops = [
            Op("circle", {"radius": p["r_outer"]}),
            Op("circle", {"radius": p["r_inner"]}),
            Op("extrude", {"distance": p["length"]}),
            Op(
                "cut",
                {
                    "plane": "XY",
                    "ops": [
                        {
                            "name": "rect",
                            "args": {
                                "length": p["r_outer"] * 2.2,
                                "width": p["slit_w"],
                            },
                        },
                        {"name": "extrude", "args": {"distance": p["length"]}},
                    ],
                },
            ),
        ]
        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags={"hollow": True, "split": True, "ref": self.REF},
        )


# 13. simple_bent_strip (sheet metal bend — N-shape strip)
class SimpleBentStripFamily(BaseFamily):
    name = "simple_bent_strip"
    standard = "N/A"
    REF = "f360:56430_4f35ba2f bent sheet metal"

    def sample_params(self, difficulty, rng):
        return {
            "leg1_h": round(float(rng.uniform(15, 35)), 1),
            "mid_h": round(float(rng.uniform(15, 35)), 1),
            "leg2_h": round(float(rng.uniform(15, 35)), 1),
            "step_x": round(float(rng.uniform(20, 40)), 1),
            "thickness_2d": round(float(rng.uniform(2, 5)), 1),
            "length": round(float(rng.uniform(30, 80)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return p["thickness_2d"] * 3 < min(p["leg1_h"], p["mid_h"], p["leg2_h"])

    def make_program(self, p):
        l1 = p["leg1_h"]
        m = p["mid_h"]
        l2 = p["leg2_h"]
        sx = p["step_x"]
        t = p["thickness_2d"]
        # N-shape sheet bend: vertical leg up, horizontal step right, vertical leg down
        # Outline (going CCW around the thin strip):
        pts = [
            (0, 0),
            (t, 0),
            (t, l1),
            (sx, l1),
            (sx, l1 - m),
            (sx + t * 2, l1 - m),
            (sx + t * 2, l1 + t),
            (t, l1 + t),
            (t, l2),
            (0, l2),
        ]
        return _emit(self, p, pts)


ALL_FAMILIES = [
    SimpleCChannelFamily,
    SimpleUChannelSimpleFamily,
    SimpleHatSectionFamily,
    SimpleZSectionStructFamily,
    SimpleIBeamSimpleFamily,
    SimpleAngleBracket90Family,
    SimpleAngleBracket135Family,
    SimpleBoxSectionFamily,
    SimpleUnistrutFamily,
    SimpleTopHatSectionFamily,
    SimpleLSectionThinFamily,
    SimpleSplitTubeFamily,
    SimpleBentStripFamily,
]
