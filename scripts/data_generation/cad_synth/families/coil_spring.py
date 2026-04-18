"""Coil spring — circular wire profile swept along a helix path (DIN 2095).

DIN 2095: preferred wire diameters d (mm) for compression coil springs.
Spring index c = D/d (mean coil dia / wire dia); DIN 2095 recommends c = 4–20.
Mean coil diameter D = 2 × coil_radius.

Easy:   plain coil (small wire d 2–4 mm)
Medium: + flat ground ends (cut top/bottom), mid range d 3–8 mm
Hard:   + variable pitch (two-section helix), full range d 2–10 mm
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 2095 Table 2 — preferred wire diameters d (mm), practical subset ≥2mm
_DIN2095_D = [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
_SMALL_D = _DIN2095_D[:4]   # 2.0–3.5 mm
_MID_D = _DIN2095_D[1:7]    # 2.5–6.0 mm
_ALL_D = _DIN2095_D


class CoilSpringFamily(BaseFamily):
    name = "coil_spring"
    standard = "DIN 2095"

    def sample_params(self, difficulty: str, rng) -> dict:
        d_pool = (
            _SMALL_D if difficulty == "easy" else (_MID_D if difficulty == "medium" else _ALL_D)
        )
        wire_d = float(d_pool[int(rng.integers(0, len(d_pool)))])
        wire_r = wire_d / 2
        # Spring index c = D/d; DIN 2095 recommends 4–20
        c = float(rng.choice([4, 5, 6, 8, 10, 12, 16, 20]))
        coil_r = round(c * wire_d / 2, 1)  # mean coil radius
        n_coils = float(rng.choice([3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]))
        pitch = round(wire_d * rng.uniform(2.5, 4.5), 2)
        height = round(pitch * n_coils, 1)

        params = {
            "wire_diameter": wire_d,
            "spring_index": c,
            "coil_radius": coil_r,
            "wire_radius": round(wire_r, 2),
            "n_coils": n_coils,
            "pitch": round(pitch, 2),
            "height": height,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            grind_depth = round(wire_r * 0.5, 2)
            params["grind_depth"] = grind_depth

        if difficulty == "hard":
            n_coils_tight = float(rng.choice([1.0, 1.5, 2.0, 2.5]))
            pitch_tight = round(wire_d * rng.uniform(2.2, 3.0), 2)
            params["tight_coils"] = n_coils_tight
            params["tight_pitch"] = pitch_tight
            params["tight_height"] = round(pitch_tight * n_coils_tight, 2)

        # helix always spirals along global Z; restrict to XY base plane
        params["base_plane"] = "XY"
        return params

    def validate_params(self, params: dict) -> bool:
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        p = params["pitch"]
        h = params["height"]

        if wr >= cr * 0.3 or wr < 1.0:
            return False
        if p < wr * 2.2:
            return False
        if h < 10 or h > 300:
            return False

        gd = params.get("grind_depth", 0)
        if gd >= wr:
            return False

        tp = params.get("tight_pitch")
        if tp and tp < wr * 2.1:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        p = params["pitch"]
        h = params["height"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Main coil: circle cross-section swept along helix
        # The circle is on XY plane at (coil_radius, 0), helix axis = Z
        ops.append(
            Op(
                "transformed",
                {
                    "offset": [cr, 0, 0],
                    "rotate": [0, 0, 0],
                },
            )
        )
        ops.append(Op("circle", {"radius": wr}))
        ops.append(
            Op(
                "sweep",
                {
                    "path_type": "helix",
                    "path_args": {
                        "pitch": p,
                        "height": h,
                        "radius": cr,
                    },
                    "isFrenet": True,
                },
            )
        )

        # Hard: extra grind at top face (simulates closed/ground ends on both ends)
        # The seat-washer approach (union+cut cylinder) fails for complex helix topology.
        # Instead just grind both ends flat using box cuts.

        # Grind flat ends: box cuts at bottom (medium+) and top (hard)
        gd = params.get("grind_depth", 0)
        if gd > 0:
            cut_w = round(cr * 3, 2)
            # Cut bottom
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "box",
                                "args": {
                                    "length": cut_w,
                                    "width": cut_w,
                                    "height": round(gd * 2, 3),
                                    "centered": True,
                                },
                            },
                        ],
                    },
                )
            )
            # Hard: also grind top end flat
            if difficulty == "hard":
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0, 0, round(h, 3)],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": cut_w,
                                        "width": cut_w,
                                        "height": round(gd * 2, 3),
                                        "centered": True,
                                    },
                                },
                            ],
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
