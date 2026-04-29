"""Clevis — U-shaped fork bracket with pin holes (DIN 71751 Gabelköpfe).

DIN 71751: clevis fork for connecting rods and links.
Two construction forms:
  Form A — fork end + threaded cylindrical SOCKET on opposite end (rod screws into bore).
  Form B — fork end + plain base (no thread).
Key proportions:
  arm_thickness b ≈ pin_diameter d; gap s = d + 1 mm.
  Form A socket: socket_diameter D ≈ 1.6·d + 2; socket_length L ≈ 3·d;
                 thread_bore (tap drill for M(d)) ≈ 0.85·d.

Easy:   base block + two arms + pin holes (small d 5–12 mm). Form B.
Medium: + chamfer on arm tips (d 8–20 mm). Form B.
Hard:   Form A — adds CYLINDRICAL THREADED SOCKET below base with central
        bore (the "螺丝固定 hole"); rod screws into bore. Full range d 5–40 mm.
        `through_bore` flag (50% chance): blind (DIN canonical, ends in stub) vs.
        through (穿到 fork base 那一头, opens into U-slot floor — DIN doesn't forbid).

Reference: DIN 71751:1985 — Fork heads (Gabelköpfe); Table (pin_d, arm_t, gap for pin_d 5–40mm)
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
_SMALL = _DIN71751[:4]  # d 5–10
_MID = _DIN71751[2:7]  # d 8–20
_ALL = _DIN71751


class ClevisFamily(BaseFamily):
    name = "clevis"
    standard = "DIN 71751"

    def sample_params(self, difficulty: str, rng) -> dict:
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else _ALL)
        )
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
            params["edge_op"] = str(rng.choice(["fillet", "chamfer"]))

        if difficulty == "hard":
            # DIN 71751 Form A: cylindrical threaded socket on opposite end of fork
            # Proportions (per DIN A): D = 1.6·d + 2, L = 3·d, bore = 0.85·d (tap drill)
            params["stub_diameter"] = round(pin_d * 1.6 + 2.0, 1)
            params["stub_height"] = round(pin_d * 3.0, 1)
            params["thread_bore_diameter"] = round(pin_d * 0.85, 1)
            # Bore can be blind (default DIN A — stops in stub) or through (穿到 fork base
            # 那一头). DIN 71751 doesn't forbid through-bore — the user request explicitly
            # added this option. ~50% chance of through-bore for variant coverage.
            params["through_bore"] = bool(rng.random() < 0.5)

        # Code-syntax: bore form + pin order swap
        params["bore_form"] = str(rng.choice(["hole", "cut"]))

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
        tbd = params.get("thread_bore_diameter", 0)
        if sd:
            total_w = 2 * arm_t + gap
            if sd >= total_w * 1.4:  # socket may be wider than base width
                return False
            if sd < pin_d * 1.2:  # socket must be wider than the pin itself
                return False
        if sh and sh < pin_d * 1.5:
            return False
        if tbd:
            if tbd >= sd - 2.0:  # bore must leave wall thickness
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

        # Edge fillet/chamfer on arm tops (推 fillet 频率)
        ch = params.get("chamfer")
        edge_op = params.get("edge_op", "chamfer")
        if ch:
            if edge_op == "fillet":
                tags["has_fillet"] = True
            else:
                tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("edges", {"selector": ">Z"}))
            if edge_op == "fillet":
                ops.append(Op("fillet", {"radius": ch}))
            else:
                ops.append(Op("chamfer", {"length": ch}))

        # Pin hole through both arms (X-direction long cylinder).
        # Drilled from `>X` face (arm outer face, 远离主体). Hole passes
        # through arm1 → gap → arm2. Use centerOption="CenterOfMass" so the
        # workplane origin sits at the face geometric center (instead of
        # inheriting prior workplane's projected origin). pin position 在 arm
        # 区底部偏一点点 (距 arm-base 接口 pin_d 的 clearance) 让 pin 离 base 近.
        # bore_form (from data-arg merge) toggles hole op vs circle+cutThruAll.
        bore_form = params.get("bore_form", "hole")
        # arm region world Z = [total_h/2 - arm_h, total_h/2]; with CoM origin at
        # face center (world Z=0), local_y = arm_bottom + pin_d ≈ near arm底部.
        pin_z_local = round(total_h / 2 - arm_h + pin_d, 4)
        ops.append(
            Op("workplane", {"selector": ">X", "center_option": "CenterOfMass"})
        )
        ops.append(Op("pushPoints", {"points": [(0.0, pin_z_local)]}))
        if bore_form == "hole":
            ops.append(Op("hole", {"diameter": round(pin_d, 4)}))
        else:
            ops.append(Op("circle", {"radius": round(pin_d / 2, 4)}))
            ops.append(Op("cutThruAll", {}))

        # DIN 71751 Form A (hard): cylindrical threaded SOCKET below the base.
        # The rod screws into a central through-bore (the "螺丝固定" hole).
        sd = params.get("stub_diameter")
        sh = params.get("stub_height")
        tbd = params.get("thread_bore_diameter")
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
            # Drill the threaded bore (axis = Z).
            # - blind (default): bore only through the stub cylinder (DIN A canonical).
            # - through: bore extends up through the base block too (opens into U-slot floor).
            if tbd:
                tags["has_hole"] = True
                through = params.get("through_bore", False)
                if through:
                    # span: stub bottom (-total_h/2 - sh) → top of base (total_h/2 - arm_h)
                    cut_h = sh + base_h + 2.0
                    cut_center_z = round(
                        ((-total_h / 2 - sh) + (total_h / 2 - arm_h)) / 2, 4
                    )
                else:
                    # blind: cut top exactly at stub-base interface (Z = -total_h/2),
                    # 2mm buffer extends BELOW stub bottom for clean Boolean — no
                    # base intrusion (preserves blind/through distinction).
                    cut_h = sh + 2.0
                    cut_center_z = round(stub_center_z - 1.0, 4)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0, 0, cut_center_z],
                                        "rotate": [0, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": round(cut_h, 4),
                                        "radius": round(tbd / 2, 4),
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
