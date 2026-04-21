"""Pillow block — ISO 113 / UCP-style bearing housing.

Rectangular base with central bore (bearing seat) and two elongated mounting
slots. ISO 113 Type UCP-series sizing: da (shaft bore), H (center height),
J (bolt hole center distance), L (base length), A (base width).

Easy:   plain block + through bore + 2 round mounting holes.
Medium: + slot2D mounting slots instead of round holes (ISO 113 standard).
Hard:   + top grease-nipple threaded hole + side fillets.

Reference: ISO 113:2010 — Plummer (pillow) block housings, Tab.1 (UCP-series).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ISO 113 UCP — (shaft_d, center_height_H, bolt_pitch_J, length_L, width_A, block_height_total)
_ISO113_UCP = [
    (12.0, 30.2, 95.0, 127.0, 38.0, 64.0),
    (17.0, 33.3, 105.0, 135.0, 42.0, 70.0),
    (20.0, 36.5, 115.0, 145.0, 46.0, 75.0),
    (25.0, 38.1, 127.0, 159.0, 49.0, 80.0),
    (30.0, 42.9, 140.0, 178.0, 54.0, 88.0),
    (35.0, 47.6, 160.0, 197.0, 62.0, 95.0),
    (40.0, 49.2, 175.0, 210.0, 65.0, 105.0),
    (50.0, 57.2, 202.0, 241.0, 74.0, 118.0),
]


class PillowBlockFamily(BaseFamily):
    name = "pillow_block"
    standard = "ISO 113"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = _ISO113_UCP[:3]
        elif difficulty == "medium":
            pool = _ISO113_UCP[2:6]
        else:
            pool = _ISO113_UCP[4:]

        da, H, J, L, A, Ht = pool[int(rng.integers(0, len(pool)))]
        bolt_d = round(da * 0.55, 1)
        bore_d = round(min(da * 1.8, A * 0.85, Ht * 0.75), 1)  # bearing OD-ish
        params = {
            "shaft_bore_diameter": bore_d,
            "center_height_H": H,
            "bolt_pitch_J": J,
            "base_length_L": L,
            "base_width_A": A,
            "block_height_Ht": Ht,
            "bolt_hole_d": bolt_d,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            # Slotted mounting holes — keep clearance to block ends
            max_slot = (L - J) * 0.7
            params["slot_length"] = round(min(bolt_d * 1.8, max_slot), 1)
        if difficulty == "hard":
            params["grease_hole_d"] = round(da * 0.2, 1)
        return params

    def validate_params(self, params: dict) -> bool:
        L = params["base_length_L"]
        A = params["base_width_A"]
        Ht = params["block_height_Ht"]
        bore = params["shaft_bore_diameter"]
        J = params["bolt_pitch_J"]
        bh = params["bolt_hole_d"]
        if L < 60 or A < 20 or Ht < 20:
            return False
        if bore >= A or bore >= Ht * 0.9:
            return False
        if J + bh >= L:
            return False
        sl = params.get("slot_length", 0)
        if sl and sl >= (L - J) * 0.8:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        L = params["base_length_L"]
        A = params["base_width_A"]
        Ht = params["block_height_Ht"]
        bore = params["shaft_bore_diameter"]
        H = params["center_height_H"]
        J = params["bolt_pitch_J"]
        bh = params["bolt_hole_d"]

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # ISO 113 UCP profile: flat base plate (wider feet) + central pedestal
        # housing the bearing bore. Pedestal height = Ht - H_base.
        H_base = round(min(max(Ht * 0.32, bore * 0.25 + 3.0), Ht * 0.5), 3)
        ped_L = round(min(L * 0.62, J * 0.72), 3)  # pedestal shorter than base
        ped_H = round(Ht - H_base, 3)

        # 1. Base plate (flat slab), centered
        ops = [
            Op("transformed", {"offset": [0, 0, H_base / 2], "rotate": [0, 0, 0]}),
            Op(
                "box",
                {"length": round(L, 3), "width": round(A, 3), "height": H_base},
            ),
        ]

        # 2. Central pedestal on top of base
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, H_base + ped_H / 2],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {
                            "name": "box",
                            "args": {
                                "length": ped_L,
                                "width": round(A, 3),
                                "height": ped_H,
                            },
                        },
                    ],
                },
            )
        )

        # 3. Dome cap on pedestal top (half-cylinder along bore axis = Y)
        dome_r = round(min(ped_H * 0.55, A * 0.45), 3)
        dome_cz = H_base + ped_H
        if dome_r > 2:
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, dome_cz],
                                    "rotate": [90, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(A, 3),
                                    "radius": dome_r,
                                },
                            },
                        ],
                    },
                )
            )

        # 4. Central shaft bore — horizontal through pedestal along Y, at z=H
        ops.append(
            Op(
                "cut",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, H],
                                "rotate": [90, 0, 0],
                            },
                        },
                        {
                            "name": "cylinder",
                            "args": {
                                "height": round(A + 2, 3),
                                "radius": round(bore / 2, 3),
                            },
                        },
                    ]
                },
            )
        )

        # 3. Mounting holes / slots at x=±J/2, y=0, through base
        sl = params.get("slot_length")
        for sign in (-1, 1):
            if sl:
                tags["has_slot"] = True
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [sign * J / 2, 0, Ht / 2],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "slot2D",
                                    "args": {
                                        "length": round(sl, 3),
                                        "width": round(bh, 3),
                                        "angle": 0,
                                    },
                                },
                                {
                                    "name": "extrude",
                                    "args": {
                                        "distance": round(Ht + 2, 3),
                                        "both": True,
                                    },
                                },
                            ]
                        },
                    )
                )
            else:
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [sign * J / 2, 0, Ht / 2],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(Ht + 2, 3),
                                        "radius": round(bh / 2, 3),
                                    },
                                },
                            ]
                        },
                    )
                )

        # 4. Grease nipple hole (hard) — top center, vertical
        gd = params.get("grease_hole_d")
        if gd:
            ops.append(
                Op(
                    "cut",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, Ht - (Ht - H) / 2],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round((Ht - H) * 2 + 2, 3),
                                    "radius": round(gd / 2, 3),
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
