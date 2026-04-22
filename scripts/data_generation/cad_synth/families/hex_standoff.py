"""Hex standoff — hexagonal prism spacer (male-female / female-female).

Easy:   hex prism + straight through-bore (female-female spacer)
Medium: hex body + externally-threaded stud on top + blind tapping-drill hole on bottom
Hard:   medium + chamfer on stud tip

Dimensions from ISO 272 / DIN 934 hex table plus standard tapping-drill diameters:
  M-size → (af, d_nom, d_tap, h_min, h_max)

Reference: ISO 272:1982 — Hexagon sizes; catalogue: KEYSTONE / HALDER male-female
  standoff series (PCB electronics hardware standards).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 272 / DIN 934 hex standoff table
# (m_size, af_mm, d_nom, d_tap, h_min, h_max) mm
# d_tap = tapping-drill Ø for metric coarse thread (~0.84·d_nom).
_ISO272 = [
    (3, 5.5, 3.0, 2.5, 5, 30),
    (4, 7.0, 4.0, 3.3, 6, 40),
    (5, 8.0, 5.0, 4.2, 8, 50),
    (6, 10.0, 6.0, 5.0, 10, 60),
    (8, 13.0, 8.0, 6.8, 12, 80),
    (10, 16.0, 10.0, 8.5, 15, 100),
    (12, 18.0, 12.0, 10.2, 18, 120),
    (16, 24.0, 16.0, 14.0, 20, 150),
    (20, 30.0, 20.0, 17.5, 25, 200),
]
_SMALL = _ISO272[:5]  # M3–M8
_MID = _ISO272[2:7]  # M5–M12
_ALL = _ISO272

# Preferred standoff height series (mm)
_H_SERIES = [
    5,
    6,
    8,
    10,
    12,
    15,
    18,
    20,
    25,
    30,
    35,
    40,
    45,
    50,
    60,
    70,
    80,
    90,
    100,
    120,
    150,
    200,
]


class HexStandoffFamily(BaseFamily):
    name = "hex_standoff"
    standard = "ISO 272"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        m_size, af, d_nom, d_tap, h_min, h_max = pool[int(rng.integers(0, len(pool)))]
        valid_h = [h for h in _H_SERIES if h_min <= h <= h_max]
        height = float(valid_h[int(rng.integers(0, len(valid_h)))])

        params = {
            "m_size": float(m_size),
            "across_flats": float(af),
            "height": height,
            "difficulty": difficulty,
        }

        if difficulty == "easy":
            # Female-female through-bore spacer: bore = clearance Ø (≈ d_nom)
            params["bore_diameter"] = float(d_nom)
        else:
            # Male-female: stud on top, blind tap-drill hole on bottom
            stud_length = float(rng.choice([4, 5, 6, 8, 10, 12]))
            stud_length = min(stud_length, height * 0.45)  # stud ≤ ~half body
            stud_length = max(stud_length, 3.0)
            params["stud_diameter"] = float(d_nom)
            params["stud_length"] = round(stud_length, 1)
            params["hole_diameter"] = float(d_tap)
            # Blind hole slightly deeper than stud for thread engagement clearance
            params["hole_depth"] = round(stud_length + 2.0, 1)

        if difficulty == "hard":
            # Small chamfer on stud tip for thread lead-in
            params["stud_chamfer"] = round(min(0.4, d_nom * 0.08), 2)

        return params

    def validate_params(self, params: dict) -> bool:
        af = params["across_flats"]
        h = params["height"]
        diff = params.get("difficulty", "easy")

        hex_inradius = af / 2  # distance from centre to flat
        if h < 5 or af < 5:
            return False

        if diff == "easy":
            bd = params["bore_diameter"]
            if bd >= hex_inradius * 1.7 or bd < 2.5:
                return False
            return True

        # medium/hard: stud on top + blind tap-drill on bottom
        sd = params["stud_diameter"]
        sl = params["stud_length"]
        hd = params["hole_diameter"]
        hdp = params["hole_depth"]
        # Stud must fit within hex inradius (so it sits on the hex top face)
        if sd >= hex_inradius * 1.6:
            return False
        # Tap hole must leave a bottom wall and not intrude past mid-body
        if hdp >= h * 0.75:
            return False
        if hd >= hex_inradius * 1.5:
            return False
        if sl < 3:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        af = params["across_flats"]
        h = params["height"]
        hex_diameter = round(af / 0.866, 3)  # across-corners

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Hex body
        ops.append(Op("polygon", {"n": 6, "diameter": hex_diameter}))
        ops.append(Op("extrude", {"distance": h}))

        if difficulty == "easy":
            # Through-bore (female-female spacer)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": params["bore_diameter"]}))
            return Program(
                family=self.name,
                difficulty=difficulty,
                params=params,
                ops=ops,
                feature_tags=tags,
            )

        # Male-female: extrude stud on top
        sd = params["stud_diameter"]
        sl = params["stud_length"]
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": round(sd / 2, 3)}))
        ops.append(Op("extrude", {"distance": sl}))

        # Optional stud-tip chamfer (hard)
        stud_ch = params.get("stud_chamfer")
        if stud_ch:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": stud_ch}))

        # Blind tap-drill hole from bottom
        ops.append(Op("workplane", {"selector": "<Z"}))
        ops.append(
            Op(
                "hole",
                {
                    "diameter": params["hole_diameter"],
                    "depth": params["hole_depth"],
                },
            )
        )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
