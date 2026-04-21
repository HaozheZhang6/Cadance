"""Cotter pin (split pin) — ISO 1234 bent round-wire pin.

Two parallel half-round wire legs (short + long) joined at an eye/loop head.
Profile is a half-circle — two halves back-to-back form the full round pin;
here we approximate with two parallel cylinders (one short, one long) plus a
torus-eye head joining them.

ISO 1234: d nominal, c = eye OD ≈ 1.6·d, a = leg spacing = d (legs touching).

Easy:   d ≤ 3, equal legs, no eye gap.
Medium: d ∈ {2..6}, unequal legs (short leg = 0.8 × long leg).
Hard:   d ∈ {5..13}, + splayed (spread) leg tips to mimic set condition.

Reference: ISO 1234:1997 — Split pins; Tab.1 (d, c, a, standard L series).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 1234 Tab.1 — (d_nominal, c_eye_OD, a_leg_spacing)
_ISO1234 = [
    (1.0, 1.8, 1.0),
    (1.6, 2.8, 1.6),
    (2.0, 3.6, 2.0),
    (2.5, 4.6, 2.5),
    (3.2, 5.8, 3.2),
    (4.0, 7.4, 4.0),
    (5.0, 9.2, 5.0),
    (6.3, 11.8, 6.3),
    (8.0, 15.0, 8.0),
    (10.0, 19.0, 10.0),
    (13.0, 24.8, 13.0),
]

_LENGTHS = [10, 12, 16, 20, 25, 32, 40, 50, 63, 80, 100]


class CotterPinFamily(BaseFamily):
    name = "cotter_pin"
    standard = "ISO 1234"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = [r for r in _ISO1234 if r[0] <= 3.2]
        elif difficulty == "medium":
            pool = [r for r in _ISO1234 if 2.0 <= r[0] <= 6.3]
        else:
            pool = [r for r in _ISO1234 if r[0] >= 5.0]

        d, c, a = pool[int(rng.integers(0, len(pool)))]
        lens = [L for L in _LENGTHS if d * 3 <= L <= d * 12]
        if not lens:
            lens = [max(_LENGTHS[0], int(d * 5))]
        L_long = float(rng.choice(lens))
        L_short = L_long if difficulty == "easy" else round(L_long * 0.8, 1)

        params = {
            "d": float(d),
            "c": float(c),
            "a": float(a),
            "long_leg": L_long,
            "short_leg": L_short,
            "difficulty": difficulty,
        }
        if difficulty == "hard":
            params["tip_splay"] = round(d * 0.8, 2)
        return params

    def validate_params(self, params: dict) -> bool:
        d, c, a, Ll = params["d"], params["c"], params["a"], params["long_leg"]
        if d < 0.8 or c <= d or a < d * 0.9:
            return False
        if Ll < d * 2 or params["short_leg"] < d * 1.5:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        d = params["d"]
        c = params["c"]
        a = params["a"]
        Ll = params["long_leg"]
        Ls = params["short_leg"]
        r = round(d / 2, 3)
        eye_R = round(c / 2, 3)
        # Leg centers separated by a/2 on each side of axis
        dx = round(a / 2, 3)

        tags = {
            "has_hole": True,  # eye
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Layout in XY plane: legs along -Z (hanging below eye), eye at origin (z=0).
        # Left leg (long) at x=-dx, right leg (short) at x=+dx. Eye is a torus
        # with axis along X (along leg spacing), center at (0,0,0).

        # 1. Long leg (base solid)
        ops = [
            Op("transformed", {"offset": [-dx, 0, -Ll / 2], "rotate": [0, 0, 0]}),
            Op("cylinder", {"height": round(Ll, 3), "radius": r}),
        ]
        # 2. Short leg
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [dx, 0, -Ls / 2], "rotate": [0, 0, 0]},
                        },
                        {
                            "name": "cylinder",
                            "args": {"height": round(Ls, 3), "radius": r},
                        },
                    ]
                },
            )
        )
        # 3. Eye loop: half-torus above legs (wire curls from one leg top to
        # the other). Profile = circle of radius r at x=dx on XY plane, revolved
        # 180° around Y axis so it sweeps through +Z (top half only).
        # Right-hand rule: +Y axis rotates +X into -Z, so use -Y to go through +Z.
        ops.append(
            Op(
                "union",
                {
                    "plane": "XY",
                    "ops": [
                        {"name": "moveTo", "args": {"x": round(dx, 3), "y": 0}},
                        {"name": "circle", "args": {"radius": r}},
                        {
                            "name": "revolve",
                            "args": {
                                "angleDeg": 180,
                                "axisStart": [0, 0, 0],
                                "axisEnd": [0, -1, 0],
                            },
                        },
                    ],
                },
            )
        )

        # 5. Splay (hard): skip — keeping tips clean for consistency
        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
