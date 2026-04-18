"""Link plate — flat slot/stadium profile plate (wire-EDM).

Oblong connecting link: two semicircular boss ends joined by straight sides.
Uniform thickness throughout — typical wire-EDM flat part.

Easy:   plain stadium extrude.
Medium: + circular through-bores in each boss.
Hard:   + lightening slot cut between bosses.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class FlatLinkFamily(BaseFamily):
    name = "flat_link"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        boss_r = round(rng.uniform(8, 30), 1)  # boss circle radius
        cc_dist = round(rng.uniform(boss_r * 1.5, boss_r * 5), 1)  # centre-to-centre
        thick = round(rng.uniform(4, 16), 1)

        params = {
            "boss_radius": boss_r,
            "cc_distance": cc_dist,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            bore_r = round(rng.uniform(boss_r * 0.25, boss_r * 0.55), 1)
            params["bore_radius"] = bore_r

        if difficulty == "hard":
            slot_w = round(rng.uniform(boss_r * 0.3, boss_r * 0.7), 1)
            params["slot_width"] = slot_w

        return params

    def validate_params(self, params: dict) -> bool:
        boss_r = params["boss_radius"]
        cc = params["cc_distance"]
        thick = params["thickness"]

        if boss_r < 6:
            return False
        if cc < boss_r * 1.2:
            return False
        if thick < 3:
            return False

        br = params.get("bore_radius", 0)
        if br and br >= boss_r * 0.65:
            return False

        sw = params.get("slot_width", 0)
        if sw and sw >= boss_r * 0.8:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        boss_r = params["boss_radius"]
        cc = params["cc_distance"]
        thick = params["thickness"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Stadium (slot) profile: slot2D(centre-to-centre, diameter)
        ops.append(
            Op("slot2D", {"length": round(cc, 4), "width": round(2 * boss_r, 4)})
        )
        ops.append(Op("extrude", {"distance": round(thick, 4)}))

        # Through bores in each boss (medium+)
        br = params.get("bore_radius")
        if br:
            tags["has_hole"] = True
            half_cc = round(cc / 2, 4)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(-half_cc, 0.0), (half_cc, 0.0)]}))
            ops.append(Op("hole", {"diameter": round(2 * br, 4)}))

        # Lightening slot between bosses (hard)
        sw = params.get("slot_width")
        if sw:
            slot_len = round(cc * 0.6, 4)
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
