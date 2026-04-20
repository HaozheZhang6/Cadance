"""Motor end cap — round flange disc with center shaft hole and bolt circle.

Typical use: motor end bell, bearing housing cover, drive-end cap.
Easy:   disc + center hole + bolt circle
Medium: + boss (raised hub) + chamfer
Hard:   + ventilation holes + fillet
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class MotorEndCapFamily(BaseFamily):
    name = "motor_end_cap"
    standard = "IEC 60072-1"

    def sample_params(self, difficulty: str, rng) -> dict:
        od = rng.uniform(60, 200)
        thick = rng.uniform(8, 25)
        shaft_d = rng.uniform(od * 0.12, od * 0.30)
        n_bolts = int(rng.choice([4, 6, 8]))
        bolt_pcd = rng.uniform(shaft_d / 2 + 6, od / 2 - 6)
        bolt_d = rng.uniform(
            3.0, max(3.1, min(8.0, (bolt_pcd * 2 * 3.14159 / n_bolts) * 0.28))
        )

        params = {
            "outer_diameter": round(od, 1),
            "thickness": round(thick, 1),
            "shaft_diameter": round(shaft_d, 1),
            "bolt_count": n_bolts,
            "bolt_pcd_radius": round(bolt_pcd, 2),
            "bolt_diameter": round(bolt_d, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            boss_od = rng.uniform(shaft_d * 1.3, max(shaft_d * 1.4, bolt_pcd * 1.6))
            boss_h = rng.uniform(thick * 0.3, thick * 0.7)
            params["boss_diameter"] = round(boss_od, 1)
            params["boss_height"] = round(boss_h, 1)
            params["chamfer_length"] = round(rng.uniform(0.4, min(2.0, thick / 8)), 1)

        if difficulty == "hard":
            # Ventilation holes — same count as bolts, clearly separated from bolt circle
            n_vent = n_bolts
            boss_r = params.get("boss_diameter", od * 0.4) / 2
            gap_needed = bolt_d / 2 + 5  # min edge-to-edge gap from bolt holes
            vent_r_max = min(5.0, (bolt_pcd - boss_r - gap_needed) / 2 - 1)
            if vent_r_max < 2.1:
                vent_r_max = 2.1
            vent_r = rng.uniform(2.0, vent_r_max)
            vpcd_low = boss_r + vent_r + 2
            vpcd_high = bolt_pcd - vent_r - gap_needed
            if vpcd_high <= vpcd_low:
                vpcd_high = vpcd_low + 1
            vent_pcd = rng.uniform(vpcd_low, vpcd_high)
            params["vent_count"] = n_vent
            params["vent_radius"] = round(vent_r, 1)
            params["vent_pcd_radius"] = round(vent_pcd, 2)
            params["fillet_radius"] = round(rng.uniform(0.5, min(2.0, thick / 8)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        od = params["outer_diameter"]
        t = params["thickness"]
        sd = params["shaft_diameter"]
        bpr = params["bolt_pcd_radius"]
        bolt_d = params["bolt_diameter"]
        n = params["bolt_count"]

        if sd >= od * 0.4 or sd < 8:
            return False
        if bpr <= sd / 2 + 4 or bpr >= od / 2 - 4:
            return False
        circ_gap = 2 * 3.14159 * bpr / n - bolt_d
        if circ_gap < 2:
            return False

        bd = params.get("boss_diameter")
        bh = params.get("boss_height")
        if bd and bh:
            if bd <= sd or bd >= od or bh >= t:
                return False

        vr = params.get("vent_radius")
        vpcd = params.get("vent_pcd_radius")
        vn = params.get("vent_count")
        if vr and vpcd and vn:
            bolt_d = params["bolt_diameter"]
            if vpcd - vr < sd / 2 + 2:
                return False
            if vpcd + vr > bpr - bolt_d / 2 - 4:  # enforce separation from bolt ring
                return False
            circ_gap_v = 2 * 3.14159 * vpcd / vn - 2 * vr
            if circ_gap_v < 2:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        od = params["outer_diameter"]
        t = params["thickness"]
        sd = params["shaft_diameter"]
        n = params["bolt_count"]
        bpr = params["bolt_pcd_radius"]
        bolt_d = params["bolt_diameter"]

        ops, tags = [], {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": True,
            "pattern_like": True,
        }

        # Base disc
        ops.append(Op("cylinder", {"height": t, "radius": od / 2}))

        # Shaft hole
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": sd}))

        # Boss (medium+)
        bd = params.get("boss_diameter")
        bh = params.get("boss_height")
        if bd and bh:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": bd / 2}))
            ops.append(Op("extrude", {"distance": bh}))

        # Chamfer (medium+) — BEFORE vent/bolt holes to avoid complex multi-circle >Z face
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Fillet (hard) — BEFORE vent/bolt holes; <Z is clean (outer+shaft circles only)
        fr = params.get("fillet_radius")
        if fr:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Ventilation holes (hard)
        vr = params.get("vent_radius")
        vpcd = params.get("vent_pcd_radius")
        vn = params.get("vent_count")
        if vr and vpcd and vn:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op(
                    "polarArray",
                    {
                        "radius": vpcd,
                        "startAngle": 0,
                        "angle": 360,
                        "count": vn,
                    },
                )
            )
            ops.append(Op("hole", {"diameter": vr * 2}))

        # Bolt circle
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(
            Op(
                "polarArray",
                {
                    "radius": bpr,
                    "startAngle": 0,
                    "angle": 360,
                    "count": n,
                },
            )
        )
        ops.append(Op("hole", {"diameter": bolt_d}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
