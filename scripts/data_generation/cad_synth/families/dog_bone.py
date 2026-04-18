"""Dog-bone plate — dumbbell/dog-bone wire-EDM flat plate.

Two large circular boss ends connected by a narrowed waist (straight tangent lines).
Used as transmission links, weight-saving connecting members.

Easy:   plain dog-bone extrude.
Medium: + axle bores through each boss.
Hard:   + lightening oval slot through waist.
"""


from ..pipeline.builder import Op, Program
from .base import BaseFamily


class DogBoneFamily(BaseFamily):
    name = "dog_bone"

    def sample_params(self, difficulty: str, rng) -> dict:
        boss_r = round(rng.uniform(12, 45), 1)
        waist_r = round(rng.uniform(boss_r * 0.3, boss_r * 0.65), 1)
        cc = round(rng.uniform(boss_r * 2.0, boss_r * 5.0), 1)
        thick = round(rng.uniform(4, 18), 1)

        params = {
            "boss_radius": boss_r,
            "waist_radius": waist_r,
            "cc_distance": cc,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            bore_r = round(rng.uniform(boss_r * 0.2, boss_r * 0.5), 1)
            params["bore_radius"] = bore_r

        if difficulty == "hard":
            slot_w = round(rng.uniform(waist_r * 0.4, waist_r * 0.75), 1)
            params["slot_width"] = slot_w

        return params

    def validate_params(self, params: dict) -> bool:
        br = params["boss_radius"]
        wr = params["waist_radius"]
        cc = params["cc_distance"]
        thick = params["thickness"]

        if br < 10:
            return False
        if wr < 5:
            return False
        if wr >= br:
            return False
        if cc < br * 1.8:
            return False
        if thick < 3:
            return False

        bore = params.get("bore_radius", 0)
        if bore and bore >= br * 0.6:
            return False

        sw = params.get("slot_width", 0)
        if sw and sw >= wr * 0.9:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        R = params["boss_radius"]  # boss circle radius
        r = params["waist_radius"]  # waist circle radius (tangent constraint)
        L = params["cc_distance"]  # centre-to-centre
        thick = params["thickness"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Dog-bone profile: two large arcs + two straight tangent lines connecting bosses.
        # Boss centres at (-L/2, 0) and (+L/2, 0).
        # Tangent line y-offset: waist_radius r (straight tangent where boss and waist radii match).
        # For simplicity use waist_r directly as the y-offset of the straight tangent lines.
        # Profile (CCW): start at (-L/2, r) → top straight line → (+L/2, r) → right boss arc →
        #                (+L/2, -r) → bottom straight line → (-L/2, -r) → left boss arc → close.

        hL = round(L / 2, 4)
        Rv = round(R, 4)
        rv = round(r, 4)

        # Mid-arc point for left boss (at angle 180° from right): (-L/2 - R, 0)
        left_mid = [round(-hL - Rv, 4), 0.0]
        # Mid-arc point for right boss: (+L/2 + R, 0)
        right_mid = [round(hL + Rv, 4), 0.0]

        ops.append(Op("moveTo", {"x": round(-hL, 4), "y": rv}))
        ops.append(Op("lineTo", {"x": round(hL, 4), "y": rv}))
        ops.append(
            Op(
                "threePointArc",
                {"point1": right_mid, "point2": [round(hL, 4), round(-rv, 4)]},
            )
        )
        ops.append(Op("lineTo", {"x": round(-hL, 4), "y": round(-rv, 4)}))
        ops.append(
            Op("threePointArc", {"point1": left_mid, "point2": [round(-hL, 4), rv]})
        )
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": round(thick, 4)}))

        # Axle bores (medium+)
        bore = params.get("bore_radius")
        if bore:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(-hL, 0.0), (hL, 0.0)]}))
            ops.append(Op("hole", {"diameter": round(2 * bore, 4)}))

        # Lightening oval slot through waist (hard)
        sw = params.get("slot_width")
        if sw:
            slot_len = round(L * 0.35, 4)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op("slot2D", {"length": round(slot_len, 4), "width": round(sw, 4)})
            )
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
