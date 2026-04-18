"""Ball knob — spherical grip on a cylindrical stem (DIN 319 ball knobs).

DIN 319 ball knobs: sphere diameter D, metric thread M, stem height H_nominal.
All (D, M, H) values from DIN 319 Table 1 (Kugelknöpfe).

Easy:   sphere + plain stem (small D 16–32 mm)
Medium: same geometry, mid range (D 25–63 mm)
Hard:   + through bore M-thread in stem (full range D 16–80 mm)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 319 ball knob table — (D_ball_mm, thread_M_mm, H_stem_nominal_mm)
_DIN319_BALL = [
    (16, 4, 30),
    (20, 5, 38),
    (25, 6, 50),
    (32, 8, 60),
    (40, 10, 75),
    (50, 12, 90),
    (63, 16, 115),
    (80, 20, 140),
]
_SMALL = _DIN319_BALL[:3]  # D 16–25
_MID = _DIN319_BALL[1:6]  # D 20–50
_ALL = _DIN319_BALL


class BallKnobFamily(BaseFamily):
    name = "ball_knob"
    standard = "DIN 319"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
        D, M, H = pool[int(rng.integers(0, len(pool)))]
        ball_r = round(D / 2, 1)
        stem_r = round(M / 2 * 1.5, 1)  # stem OD ≈ 1.5 × thread minor radius
        stem_h = float(H)

        params = {
            "ball_diameter": float(D),
            "thread_m": float(M),
            "ball_radius": ball_r,
            "stem_radius": stem_r,
            "stem_height": stem_h,
            "difficulty": difficulty,
        }

        if difficulty == "hard":
            params["bore_diameter"] = float(M)  # M-thread through bore

        return params

    def validate_params(self, params: dict) -> bool:
        ball_r = params["ball_radius"]
        stem_r = params["stem_radius"]
        stem_h = params["stem_height"]

        if ball_r < 8:
            return False
        if stem_r < 4:
            return False
        if stem_r >= ball_r * 0.6:
            return False
        if stem_h < 10:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ball_r = params["ball_radius"]
        stem_r = params["stem_radius"]
        stem_h = params["stem_height"]

        ops = []
        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        # Sphere (ball) centred at origin
        ops.append(Op("sphere", {"radius": round(ball_r, 4)}))

        # Stem: cylinder pointing downward from sphere.
        stem_cz = round(-(ball_r + stem_h / 2), 4)
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0.0, 0.0, stem_cz],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": round(stem_h, 4),
                                "radius": round(stem_r, 4),
                            },
                        },
                    ]
                },
            )
        )

        # Through bore (hard) — along Z axis through stem and into ball
        bore_d = params.get("bore_diameter", 0)
        if bore_d:
            tags["has_hole"] = True
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, -(ball_r + stem_h)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(ball_r + stem_h + ball_r, 4),
                                    "radius": round(bore_d / 2, 4),
                                },
                            },
                        ]
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
