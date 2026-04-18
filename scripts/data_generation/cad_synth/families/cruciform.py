"""Cross plate — plus/cross-shaped wire-EDM plate.

Two overlapping rectangular arms forming a + cross profile, extruded to thickness.
Common as structural spacers, cross-shaped mounting plates, X-braces.

Easy:   symmetric + cross extrude.
Medium: + center through hole.
Hard:   + through holes at each arm tip.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class CruciformFamily(BaseFamily):
    name = "cruciform"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        arm_len = round(rng.uniform(20, 80), 1)  # half-length of each arm
        arm_w = round(rng.uniform(10, 40), 1)  # width of each arm
        thick = round(rng.uniform(3, 14), 1)

        # Clamp: arm width must be < arm length
        arm_w = min(arm_w, arm_len * 0.8)

        params = {
            "arm_length": arm_len,
            "arm_width": arm_w,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            ctr_r = round(rng.uniform(arm_w * 0.2, arm_w * 0.45), 1)
            params["center_hole_radius"] = ctr_r

        if difficulty == "hard":
            tip_r = round(rng.uniform(arm_w * 0.15, arm_w * 0.35), 1)
            params["tip_hole_radius"] = tip_r

        return params

    def validate_params(self, params: dict) -> bool:
        al = params["arm_length"]
        aw = params["arm_width"]
        thick = params["thickness"]

        if al < 15:
            return False
        if aw < 8:
            return False
        if aw >= al:
            return False
        if thick < 2:
            return False

        cr = params.get("center_hole_radius", 0)
        if cr and cr >= aw * 0.5:
            return False

        tr = params.get("tip_hole_radius", 0)
        if tr and tr >= aw * 0.4:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        al = params["arm_length"]
        aw = params["arm_width"]
        thick = params["thickness"]

        hw = round(aw / 2, 4)  # half arm width
        ha = round(al, 4)  # half-arm length (extends from centre)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Cross profile: 12-point polygon tracing the + shape (clockwise from top-right corner)
        #  (+hw, +hw) → (+ha, +hw) → (+ha, -hw) → (+hw, -hw)
        #  → (+hw, -ha) → (-hw, -ha) → (-hw, -hw) → (-ha, -hw)
        #  → (-ha, +hw) → (-hw, +hw) → (-hw, +ha) → (+hw, +ha) → close
        pts = [
            (hw, hw),
            (ha, hw),
            (ha, -hw),
            (hw, -hw),
            (hw, -ha),
            (-hw, -ha),
            (-hw, -hw),
            (-ha, -hw),
            (-ha, hw),
            (-hw, hw),
            (-hw, ha),
            (hw, ha),
        ]
        ops.append(
            Op("polyline", {"points": [[round(x, 4), round(y, 4)] for x, y in pts]})
        )
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": round(thick, 4)}))

        # Center hole (medium+)
        cr = params.get("center_hole_radius")
        if cr:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(0.0, 0.0)]}))
            ops.append(Op("hole", {"diameter": round(2 * cr, 4)}))

        # Tip holes (hard) — one per arm end
        tr = params.get("tip_hole_radius")
        if tr:
            tags["has_hole"] = True
            tip_pts = [
                (ha - round(2 * tr, 4), 0.0),
                (-(ha - round(2 * tr, 4)), 0.0),
                (0.0, ha - round(2 * tr, 4)),
                (0.0, -(ha - round(2 * tr, 4))),
            ]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op(
                    "pushPoints",
                    {"points": [[round(x, 4), round(y, 4)] for x, y in tip_pts]},
                )
            )
            ops.append(Op("hole", {"diameter": round(2 * tr, 4)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
