"""Hex standoff / hex bolt boss — hexagonal prism with through bore.

Structural type: polygon cross-section. Completely different from round or square bodies.
Covers: hex spacers, standoffs, hex bosses, hex flanged nuts.

Dimensions from ISO 272 / DIN 934 wrench-size table: M-size → (af_mm, bore_d, h_min, h_max).

Easy:   hex prism + center bore
Medium: + flange base + chamfer
Hard:   + partial blind bore (stepped) + fillet
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 272 / DIN 934 hex standoff table — (m_size, af_mm, bore_d, h_min, h_max) mm
_ISO272 = [
    (3, 5.5, 3.0, 5, 30),
    (4, 7.0, 4.0, 6, 40),
    (5, 8.0, 5.0, 8, 50),
    (6, 10.0, 6.0, 10, 60),
    (8, 13.0, 8.0, 12, 80),
    (10, 16.0, 10.0, 15, 100),
    (12, 18.0, 12.0, 18, 120),
    (16, 24.0, 16.0, 20, 150),
    (20, 30.0, 20.0, 25, 200),
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
        m_size, af, bore_d, h_min, h_max = pool[int(rng.integers(0, len(pool)))]
        valid_h = [h for h in _H_SERIES if h_min <= h <= h_max]
        height = float(valid_h[int(rng.integers(0, len(valid_h)))])

        params = {
            "m_size": float(m_size),
            "across_flats": float(af),
            "height": height,
            "bore_diameter": float(bore_d),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Flange base (larger hex or round disc)
            flange_od = rng.uniform(af * 1.3, af * 1.8)
            flange_h = rng.uniform(2, max(2.5, min(8, height * 0.25)))

            params["flange_diameter"] = round(flange_od, 1)
            params["flange_height"] = round(flange_h, 1)
            params["chamfer_length"] = round(
                rng.uniform(0.5, max(0.6, min(2.0, height * 0.04))), 1
            )

        if difficulty == "hard":
            # Stepped bore: larger bore for top portion, smaller for bottom
            bsd_low = bore_d * 1.3
            bsd_high = max(bsd_low + 1, af * 0.65)
            bore_step_d = rng.uniform(bsd_low, bsd_high)
            bore_step_h = rng.uniform(2, max(2.5, min(8, height * 0.3)))
            params["bore_step_diameter"] = round(bore_step_d, 1)
            params["bore_step_height"] = round(bore_step_h, 1)
            params["fillet_radius"] = round(
                rng.uniform(0.3, max(0.4, min(1.0, af * 0.03))), 1
            )

        return params

    def validate_params(self, params: dict) -> bool:
        af = params["across_flats"]
        h = params["height"]
        bd = params["bore_diameter"]

        # hex circumradius = af / cos(30°) ≈ af / 0.866
        hex_r = af / 0.866
        if bd >= hex_r * 0.85 or bd < 3:
            return False
        if h < 5 or af < 6:
            return False

        flange_d = params.get("flange_diameter")
        flange_h = params.get("flange_height")
        if flange_d and flange_h:
            if flange_d <= af or flange_h >= h:
                return False

        bsd = params.get("bore_step_diameter")
        bsh = params.get("bore_step_height")
        if bsd and bsh:
            if bsd >= hex_r * 0.85:
                return False
            if bsh >= h * 0.5:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        af = params["across_flats"]
        h = params["height"]
        bd = params["bore_diameter"]

        # polygon diameter = across-flats / cos(30°) * 1 = circumradius*2
        # CadQuery polygon(n, diameter) takes circumradius*2 (across-corners)
        hex_diameter = round(af / 0.866, 3)

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

        # Flange base (medium+)
        flange_d = params.get("flange_diameter")
        flange_h = params.get("flange_height")
        if flange_d and flange_h:
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("circle", {"radius": flange_d / 2}))
            ops.append(Op("extrude", {"distance": flange_h}))

        # Through bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": bd}))

        # Stepped bore (hard)
        bsd = params.get("bore_step_diameter")
        bsh = params.get("bore_step_height")
        if bsd and bsh:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": bsd / 2}))
            ops.append(Op("cutBlind", {"depth": bsh}))

        # Chamfer top edges (medium+)
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Fillet (hard)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
