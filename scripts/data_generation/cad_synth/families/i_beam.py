"""I-beam / H-section structural member — IPE series (EN 10034).

Geometry: H/I cross-section; polyline half-profile + mirrorY + extrude.
Dimensions sampled ONLY from the IPE rolled steel section table.
Length (cut-to-length dimension) is sampled in range [3h, 10h].

Table columns: (designation, h_height, b_flange, tw_web, tf_flange) — all mm.

Easy:   IPE80–IPE200 (small sections), plain section.
Medium: IPE160–IPE360 (medium); + bolt holes in flanges + chamfer.
Hard:   full IPE80–IPE600 range; + web lightening holes + fillet.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# IPE series — EN 10034 (Euronorm 19-57) exact nominal values (mm)
# (designation, h, b, tw, tf)
_IPE = [
    ("IPE80", 80, 46, 3.8, 5.2),
    ("IPE100", 100, 55, 4.1, 5.7),
    ("IPE120", 120, 64, 4.4, 6.3),
    ("IPE140", 140, 73, 4.7, 6.9),
    ("IPE160", 160, 82, 5.0, 7.4),
    ("IPE180", 180, 91, 5.3, 8.0),
    ("IPE200", 200, 100, 5.6, 8.5),
    ("IPE220", 220, 110, 5.9, 9.2),
    ("IPE240", 240, 120, 6.2, 9.8),
    ("IPE270", 270, 135, 6.6, 10.2),
    ("IPE300", 300, 150, 7.1, 10.7),
    ("IPE330", 330, 160, 7.5, 11.5),
    ("IPE360", 360, 170, 8.0, 12.7),
    ("IPE400", 400, 180, 8.6, 13.5),
    ("IPE450", 450, 190, 9.4, 14.6),
    ("IPE500", 500, 200, 10.2, 16.0),
    ("IPE550", 550, 210, 11.1, 17.2),
    ("IPE600", 600, 220, 12.0, 19.0),
]

_SMALL = [r for r in _IPE if r[1] <= 200]  # IPE80–IPE200
_MEDIUM = [r for r in _IPE if 160 <= r[1] <= 360]  # IPE160–IPE360
_ALL = _IPE


class IBeamFamily(BaseFamily):
    name = "i_beam"
    standard = "EN 10034"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _SMALL
        elif difficulty == "medium":
            pool = _MEDIUM
        else:
            pool = _ALL

        desig, h, b, tw, tf = pool[int(rng.integers(0, len(pool)))]

        # Cut-to-length: 3h–10h, snapped to nearest 50 mm
        min_l = max(100, h * 3)
        max_l = h * 10
        raw_l = rng.uniform(min_l, max_l)
        length = round(raw_l / 50) * 50
        length = max(length, 100)

        params = {
            "designation": desig,
            "flange_width": float(b),
            "total_height": float(h),
            "flange_thickness": float(tf),
            "web_thickness": float(tw),
            "length": float(length),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            n_bolt = int(rng.choice([2, 3, 4]))
            bolt_d = round(rng.uniform(4.0, max(5.0, tf * 0.6)), 1)
            bolt_d = round(min(bolt_d, tf * 0.7), 1)
            params["flange_bolt_count"] = n_bolt
            params["flange_bolt_diameter"] = bolt_d
            params["chamfer_length"] = round(min(tf * 0.15, 2.0), 1)

        if difficulty == "hard":
            params["fillet_radius"] = round(min(tw * 0.3, 2.0), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        fw = params["flange_width"]
        th = params["total_height"]
        ft = params["flange_thickness"]
        wt = params["web_thickness"]
        l = params["length"]

        if ft >= th / 2 or wt >= fw / 2:
            return False
        if ft < 2 or wt < 2 or l < 20:
            return False
        web_h = th - 2 * ft
        if web_h < 8:
            return False

        bd = params.get("flange_bolt_diameter")
        if bd and bd >= ft:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        fw = params["flange_width"]
        th = params["total_height"]
        ft = params["flange_thickness"]
        wt = params["web_thickness"]
        l = params["length"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "symmetric_result": True,
        }

        # Right-half cross-section (mirrorY → full I)
        hfw = round(fw / 2, 3)
        hwt = round(wt / 2, 3)
        web_h = round(th - 2 * ft, 3)

        pts = [
            (0.0, 0.0),
            (hfw, 0.0),
            (hfw, ft),
            (hwt, ft),
            (hwt, ft + web_h),
            (hfw, ft + web_h),
            (hfw, th),
            (0.0, th),
        ]

        ops.append(Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}))
        for px, py in pts[1:]:
            ops.append(Op("lineTo", {"x": px, "y": py}))
        ops.append(Op("mirrorY", {}))
        ops.append(Op("extrude", {"distance": l}))

        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Y"}))
            ops.append(Op("chamfer", {"length": cl}))

        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Y"}))
            ops.append(Op("fillet", {"radius": fr}))

        n_bolt = params.get("flange_bolt_count")
        bolt_d = params.get("flange_bolt_diameter")
        if n_bolt and bolt_d:
            tags["has_hole"] = True
            bolt_spacing = l / (n_bolt + 1)
            ops.append(Op("workplane", {"selector": ">Y"}))
            bolt_pts = [
                (0.0, round(-l / 2 + bolt_spacing * (i + 1), 3)) for i in range(n_bolt)
            ]
            ops.append(Op("pushPoints", {"points": bolt_pts}))
            ops.append(Op("hole", {"diameter": bolt_d}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
