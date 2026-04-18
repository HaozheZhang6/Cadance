"""Star plate — N-pointed star / sprocket blank wire-EDM plate.

Regular N-pointed star profile extruded to uniform thickness.
Outer tips at radius R_outer, inner valleys at radius R_inner.
Used as star sprockets, decorative plates, index plates.

Easy:   4-point star plain extrude.
Medium: 5-point star + center bore.
Hard:   6-point star + center bore + lightening holes at tips.
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class StarBlankFamily(BaseFamily):
    name = "star_blank"
    standard = "N/A"

    _N_BY_DIFF = {"easy": 4, "medium": 5, "hard": 6}

    def sample_params(self, difficulty: str, rng) -> dict:
        n = self._N_BY_DIFF.get(difficulty, 4)
        outer_r = round(rng.uniform(25, 80), 1)
        inner_r = round(rng.uniform(outer_r * 0.35, outer_r * 0.65), 1)
        thick = round(rng.uniform(4, 16), 1)

        params = {
            "n_points": n,
            "outer_radius": outer_r,
            "inner_radius": inner_r,
            "thickness": thick,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            bore_r = round(rng.uniform(inner_r * 0.15, inner_r * 0.40), 1)
            params["bore_radius"] = bore_r

        if difficulty == "hard":
            # Max hole radius = 70% of actual star half-width at the hole center
            hole_r_off = outer_r * 0.78
            cos_pn = math.cos(math.pi / n)
            sin_pn = math.sin(math.pi / n)
            denom = outer_r - inner_r * cos_pn
            if denom > 0.1:
                t_p = (outer_r - hole_r_off) / denom
                y_half = t_p * inner_r * sin_pn
            else:
                y_half = 1.5
            max_tr = max(0.5, y_half * 0.65 - 0.3)
            tip_hole_r = round(rng.uniform(0.5, max(0.6, min(3.0, max_tr))), 1)
            params["tip_hole_radius"] = tip_hole_r

        return params

    def validate_params(self, params: dict) -> bool:
        n = params["n_points"]
        R = params["outer_radius"]
        r = params["inner_radius"]
        thick = params["thickness"]

        if n < 3:
            return False
        if R < 18:
            return False
        if r < 8:
            return False
        if r >= R * 0.75:
            return False
        if thick < 3:
            return False

        br = params.get("bore_radius", 0)
        if br and br >= r * 0.45:
            return False

        tr = params.get("tip_hole_radius", 0)
        if tr:
            if tr >= (R - r) * 0.4:
                return False
            # Hole must fit within actual star tip width at hole center
            hole_r_off = R * 0.78
            cos_pn = math.cos(math.pi / n)
            sin_pn = math.sin(math.pi / n)
            denom = R - r * cos_pn
            if denom > 0.1:
                t_p = (R - hole_r_off) / denom
                y_half = t_p * r * sin_pn
                if tr >= y_half - 0.3:
                    return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        n = params["n_points"]
        R = params["outer_radius"]
        r = params["inner_radius"]
        thick = params["thickness"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Star profile: alternating outer (tip) and inner (valley) vertices.
        # Tip at angle (2π*k/n), valley at angle (2π*k/n + π/n).
        pts = []
        for k in range(n):
            tip_ang = 2 * math.pi * k / n - math.pi / 2  # start from top
            val_ang = tip_ang + math.pi / n
            pts.append(
                [round(R * math.cos(tip_ang), 4), round(R * math.sin(tip_ang), 4)]
            )
            pts.append(
                [round(r * math.cos(val_ang), 4), round(r * math.sin(val_ang), 4)]
            )

        ops.append(Op("polyline", {"points": pts}))
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": round(thick, 4)}))

        # Center bore (medium+)
        br = params.get("bore_radius")
        if br:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": [(0.0, 0.0)]}))
            ops.append(Op("hole", {"diameter": round(2 * br, 4)}))

        # Tip holes (hard)
        tr = params.get("tip_hole_radius")
        if tr:
            tags["has_hole"] = True
            tip_pts = []
            hole_r_off = round(R * 0.78, 4)
            for k in range(n):
                ang = 2 * math.pi * k / n - math.pi / 2
                tip_pts.append(
                    [
                        round(hole_r_off * math.cos(ang), 4),
                        round(hole_r_off * math.sin(ang), 4),
                    ]
                )
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": tip_pts}))
            ops.append(Op("hole", {"diameter": round(2 * tr, 4)}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
