"""Turnbuckle body — DIN 1480 open-frame tensioner.

Elongated frame with two cylindrical end-bosses (one LH and one RH thread in
real use; geometry here is symmetric). Central window cut allows visual
inspection of engagement.

Keys: d (thread size), L1 (frame interior length), b (frame bar width).

Easy:   two end bosses joined by two parallel bars (open frame visible).
Medium: same open frame, larger sizes (M8–M16).
Hard:   + internal-thread bore at each end boss.

Reference: DIN 1480:2007 — Turnbuckles; Tab.1 (d1, L1, b for M6..M36).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 1480 Form B (welded / open) — (thread_M, L1, b, boss_outer_d, boss_length)
_DIN1480 = {
    "M6": {"L1": 60, "b": 6, "boss_d": 14, "boss_L": 18},
    "M8": {"L1": 80, "b": 8, "boss_d": 18, "boss_L": 24},
    "M10": {"L1": 100, "b": 10, "boss_d": 22, "boss_L": 30},
    "M12": {"L1": 120, "b": 12, "boss_d": 26, "boss_L": 36},
    "M16": {"L1": 160, "b": 16, "boss_d": 34, "boss_L": 48},
    "M20": {"L1": 200, "b": 20, "boss_d": 42, "boss_L": 60},
}


class TurnbuckleFamily(BaseFamily):
    name = "turnbuckle"
    standard = "DIN 1480"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = ["M6", "M8", "M10"]
        elif difficulty == "medium":
            pool = ["M8", "M10", "M12", "M16"]
        else:
            pool = ["M12", "M16", "M20"]
        sz = str(rng.choice(pool))
        row = _DIN1480[sz]
        params = {
            "thread_size": sz,
            "d": float(int(sz[1:])),
            "L1": float(row["L1"]),
            "b": float(row["b"]),
            "boss_d": float(row["boss_d"]),
            "boss_L": float(row["boss_L"]),
            "difficulty": difficulty,
        }
        if difficulty == "hard":
            params["thread_bore_d"] = float(int(sz[1:]))
        return params

    def validate_params(self, params: dict) -> bool:
        L1 = params["L1"]
        b = params["b"]
        if L1 < 40 or b < 4 or params["boss_d"] < b * 1.2:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        L1 = params["L1"]
        b = params["b"]
        boss_d = params["boss_d"]
        boss_L = params["boss_L"]
        total_L = L1 + 2 * boss_L
        boss_r = round(boss_d / 2, 3)

        tags = {
            "has_hole": False,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Oblong body between the two bosses. Body cross-section (Y × Z) is
        # bigger than boss diameter so the frame is clearly visible, then a
        # rectangular window is cut through Z revealing the open center.
        body_h = round(boss_d * 1.3, 3)
        body_w = round(boss_d * 1.3, 3)

        # Body extends slightly past L1/2 on each side so it fuses with the
        # end bosses (whose inward faces are at x=±L1/2).
        body_overlap = round(boss_L * 0.15, 3)
        body_L = round(L1 + 2 * body_overlap, 3)

        ops = [
            Op("transformed", {"offset": [0, 0, 0], "rotate": [0, 0, 0]}),
            Op(
                "box",
                {
                    "length": body_L,
                    "width": body_w,
                    "height": body_h,
                },
            ),
        ]

        # End bosses: cylinders oriented along X
        for sign in (-1, 1):
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [sign * (L1 + boss_L) / 2, 0, 0],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(boss_L, 3),
                                    "radius": boss_r,
                                },
                            },
                        ]
                    },
                )
            )

        # Inspection windows — cut through Z and Y so the open frame is
        # visible from every angle.
        win_L = round(L1 * 0.75, 3)
        win_W = round(body_w * 0.6, 3)
        win_H = round(body_h * 0.6, 3)
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, 0], "rotate": [0, 0, 0]},
                        },
                        {
                            "name": "box",
                            "args": {
                                "length": win_L,
                                "width": win_W,
                                "height": round(body_h + 2, 3),
                            },
                        },
                    ]
                },
            )
        )
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0, 0, 0], "rotate": [0, 0, 0]},
                        },
                        {
                            "name": "box",
                            "args": {
                                "length": win_L,
                                "width": round(body_w + 2, 3),
                                "height": win_H,
                            },
                        },
                    ]
                },
            )
        )

        # 4. Thread bores at each boss (hard) — horizontal along X axis
        tb = params.get("thread_bore_d")
        if tb:
            tags["has_hole"] = True
            for sign in (-1, 1):
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [
                                            sign * (L1 + boss_L) / 2,
                                            0,
                                            0,
                                        ],
                                        "rotate": [0, 90, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(boss_L + 2, 3),
                                        "radius": round(tb / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        params["total_length"] = round(total_L, 1)
        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
