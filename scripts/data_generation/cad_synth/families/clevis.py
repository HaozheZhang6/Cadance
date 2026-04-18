"""Clevis — U-shaped fork bracket with pin holes (DIN 71751 Gabelköpfe).

DIN 71751: clevis fork for connecting rods and links.
Key proportions: arm_thickness b ≈ pin_diameter d; gap s = d + 1 mm.

Easy:   base block + two arms + pin holes (small d 5–12 mm).
Medium: + chamfer on arm tips (d 8–20 mm).
Hard:   + threaded base stub (full range d 5–40 mm).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# DIN 71751 Gabelkopf — (pin_d, arm_t, gap) mm; gap = d+1, arm_t ≈ d
_DIN71751 = [
    (5, 5, 6),
    (6, 6, 7),
    (8, 8, 9),
    (10, 10, 11),
    (12, 12, 13),
    (16, 16, 17),
    (20, 20, 21),
    (25, 25, 26),
    (32, 30, 33),
    (40, 36, 41),
]
_SMALL = _DIN71751[:4]   # d 5–10
_MID = _DIN71751[2:7]    # d 8–20
_ALL = _DIN71751


class ClevisFamily(BaseFamily):
    name = "clevis"
    standard = "DIN 71751"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = _SMALL if difficulty == "easy" else (_MID if difficulty == "medium" else _ALL)
        pin_d, arm_t, gap = pool[int(rng.integers(0, len(pool)))]
        arm_h = round(pin_d * rng.uniform(2.5, 5.0), 1)
        base_h = round(pin_d * rng.uniform(1.5, 3.0), 1)
        depth = round((2 * arm_t + gap) * rng.uniform(0.8, 1.5), 1)

        params = {
            "arm_thickness": float(arm_t),
            "gap_width": float(gap),
            "arm_height": arm_h,
            "base_height": base_h,
            "depth": depth,
            "pin_diameter": float(pin_d),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer"] = round(min(arm_t * 0.12, 2.0), 1)

        if difficulty == "hard":
            params["stub_diameter"] = round((gap + arm_t) * 0.75, 1)
            params["stub_height"] = round(base_h * 0.7, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        arm_t = params["arm_thickness"]
        gap = params["gap_width"]
        arm_h = params["arm_height"]
        base_h = params["base_height"]
        depth = params["depth"]
        pin_d = params["pin_diameter"]

        if arm_t < 4:
            return False
        if gap < 6:
            return False
        if arm_h < 12:
            return False
        if base_h < 8:
            return False
        if pin_d > arm_t:
            return False
        if depth < 10:
            return False

        ch = params.get("chamfer", 0)
        if ch and ch >= arm_t * 0.4:
            return False

        sd = params.get("stub_diameter", 0)
        sh = params.get("stub_height", 0)
        if sd:
            total_w = 2 * arm_t + gap
            if sd >= total_w * 0.95:
                return False
        if sh and sh >= base_h:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        arm_t = params["arm_thickness"]
        gap = params["gap_width"]
        arm_h = params["arm_height"]
        base_h = params["base_height"]
        depth = params["depth"]
        pin_d = params["pin_diameter"]

        total_w = 2 * arm_t + gap  # X extent
        total_h = base_h + arm_h  # Z extent (height)

        ops = []
        tags = {"has_hole": True, "has_fillet": False, "has_chamfer": False}

        # Full block: X=total_w, Y=depth, Z=total_h (centered)
        ops.append(Op("box", {"length": total_w, "width": depth, "height": total_h}))

        # Cut center slot from top (">Z"): removes inner gap over arm_h
        # slot is: length=gap(X), width=depth(Y), cut depth=arm_h in -Z
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rect", {"length": round(gap, 4), "width": round(depth + 1, 4)}))
        ops.append(Op("cutBlind", {"depth": round(arm_h, 4)}))

        # Chamfer top edges of arms (medium+)
        ch = params.get("chamfer")
        if ch:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": ch}))

        # Pin holes through each arm (Z direction from ">Z" face)
        # Arms are at x = ±(gap/2 + arm_t/2)
        arm_cx = round(gap / 2 + arm_t / 2, 4)

        # From ">Z" workplane (local_x=X_world, local_y=Y_world):
        # pushPoints at (x_world, y_world=0) but ">Z" face is the TOP of the L —
        # HOWEVER: after the slot cut, the ">Z" face consists of the two arm tops.
        # Drilling at (±arm_cx, 0) should land on each arm.
        # We use separate pushPoints + hole to ensure clarity.
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(
            Op(
                "pushPoints",
                {
                    "points": [
                        (round(-arm_cx, 4), 0.0),
                        (round(+arm_cx, 4), 0.0),
                    ]
                },
            )
        )
        ops.append(Op("hole", {"diameter": round(pin_d, 4)}))

        # Threaded base stub (hard): cylinder protruding below base
        sd = params.get("stub_diameter")
        sh = params.get("stub_height")
        if sd and sh:
            stub_center_z = round(-(total_h / 2 + sh / 2), 4)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, stub_center_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(sh, 4),
                                    "radius": round(sd / 2, 4),
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
