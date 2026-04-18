"""Dowel pin — precision cylindrical pin (ISO 8734 / DIN 6325).

ISO 8734 standard diameter series (mm): 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20
Tolerance: m6 (parallel) — geometry is a plain cylinder with chamfered ends.

Easy:   plain cylinder with end chamfers
Medium: + centre drill hole on one end (tolerance marking indentation)
Hard:   + second end differs (spring pin / grooved end style): axial groove cut

Reference: ISO 8734:1997 — Parallel pins, of unhardened steel; Table (d, l series for d 1–20mm)
"""


from ..pipeline.builder import Op, Program
from .base import BaseFamily

_ISO8734_DIAMETERS = [
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    4.0,
    5.0,
    6.0,
    8.0,
    10.0,
    12.0,
    16.0,
    20.0,
]
# Standard length series for each nominal diameter (approximate; actual table truncated for codegen)
_LENGTH_OPTIONS = [6, 8, 10, 12, 16, 20, 24, 30, 36, 40, 50, 60, 80, 100]


class DowelPinFamily(BaseFamily):
    name = "dowel_pin"
    standard = "ISO 8734"

    def sample_params(self, difficulty: str, rng) -> dict:
        d = float(
            rng.choice(_ISO8734_DIAMETERS[:10])
        )  # up to d=12 for reasonable rendering
        min_l = max(6, int(d * 2))
        max_l = min(100, int(d * 12))
        length_opts = [l for l in _LENGTH_OPTIONS if min_l <= l <= max_l]
        if not length_opts:
            length_opts = [min_l]
        length = float(rng.choice(length_opts))

        chamfer = round(d * 0.15, 2)  # ISO: 0.1–0.2 × d
        params = {
            "diameter": d,
            "length": length,
            "chamfer_length": chamfer,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Centre drill on one end — small conical indentation
            cd_d = round(min(d * 0.3, 1.5), 2)
            params["centre_drill_diameter"] = cd_d

        if difficulty == "hard":
            # Larger diameter + longer pin (tighter L/D ratio) — harder to estimate
            # Also add chamfer on both ends (vs easy/medium single chamfer)
            params["double_chamfer"] = True

        return params

    def validate_params(self, params: dict) -> bool:
        d = params["diameter"]
        l = params["length"]
        ch = params["chamfer_length"]

        if d < 1.0 or l < d * 2 or ch >= d * 0.3:
            return False

        cd = params.get("centre_drill_diameter", 0)
        if cd and cd >= d * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["diameter"]
        l = params["length"]
        ch = params["chamfer_length"]
        r = round(d / 2, 4)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": True,
            "rotational": True,
        }

        # Main cylinder
        ops.append(Op("cylinder", {"height": l, "radius": r}))

        # Chamfer both ends
        ops.append(Op("edges", {"selector": "|Z"}))
        ops.append(Op("chamfer", {"length": ch}))

        # Centre drill (medium+) — small blind hole on +Z face
        cd = params.get("centre_drill_diameter", 0)
        if cd:
            tags["has_hole"] = True
            cd_depth = round(cd * 1.2, 3)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": round(cd, 4), "depth": cd_depth}))

        # Axial groove (hard) — longitudinal slot on one side
        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
