"""Ball knob — spherical grip on a cylindrical stem (DIN 319 ball knobs).

DIN 319 ball knobs: sphere diameter D, metric thread M, stem height H_nominal.
All (D, M, H) values from DIN 319 Table 1 (Kugelknöpfe).

Easy:   sphere + plain stem (small D 16–32 mm)
Medium: same geometry, mid range (D 25–63 mm)
Hard:   + through bore M-thread in stem (full range D 16–80 mm)

Reference: DIN 319:1991 — Control knobs, Form C (ball); Table (D, M, H for D 16–80mm)
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

        # Code-syntax: A↔B (stem first vs sphere first) + cylinder/extrude form
        params["stem_first"] = bool(rng.random() < 0.5)
        params["stem_form"] = str(rng.choice(["cylinder", "extrude"]))
        # Bottom-of-stem edge mod (medium/hard, 50%)
        if difficulty in ("medium", "hard") and rng.random() < 0.5:
            params["stem_tip_op"] = str(rng.choice(["chamfer", "fillet"]))
            params["stem_tip_size"] = round(stem_r * 0.15, 2)

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

        stem_first = bool(params.get("stem_first", False))
        stem_form = params.get("stem_form", "cylinder")
        ops = []
        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
        }

        stem_cz = round(-(ball_r + stem_h / 2), 4)
        # Stem ops (cylinder vs circle.extrude form)
        if stem_form == "cylinder":
            stem_sub_ops = [
                {
                    "name": "transformed",
                    "args": {"offset": [0.0, 0.0, stem_cz], "rotate": [0, 0, 0]},
                },
                {
                    "name": "cylinder",
                    "args": {"height": round(stem_h, 4), "radius": round(stem_r, 4)},
                },
            ]
        else:
            stem_sub_ops = [
                {
                    "name": "transformed",
                    "args": {
                        "offset": [0.0, 0.0, round(-(ball_r + stem_h), 4)],
                        "rotate": [0, 0, 0],
                    },
                },
                {"name": "circle", "args": {"radius": round(stem_r, 4)}},
                {"name": "extrude", "args": {"distance": round(stem_h, 4)}},
            ]

        if stem_first:
            # Stem primary, sphere unioned in.
            for sub in stem_sub_ops:
                ops.append(Op(sub["name"], sub["args"]))
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "sphere",
                                "args": {"radius": round(ball_r, 4)},
                            }
                        ]
                    },
                )
            )
        else:
            # Sphere primary, stem unioned in (original order).
            ops.append(Op("sphere", {"radius": round(ball_r, 4)}))
            ops.append(Op("union", {"ops": stem_sub_ops}))

        # Stem tip edge mod (medium/hard) — chamfer/fillet on bottom circle.
        stem_tip_op = params.get("stem_tip_op")
        stem_tip_size = float(params.get("stem_tip_size", 0.0))
        if stem_tip_op and stem_tip_size > 0:
            if stem_tip_op == "fillet":
                tags["has_fillet"] = True
            else:
                tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("edges", {}))
            if stem_tip_op == "fillet":
                ops.append(Op("fillet", {"radius": stem_tip_size}))
            else:
                ops.append(Op("chamfer", {"length": stem_tip_size}))

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
