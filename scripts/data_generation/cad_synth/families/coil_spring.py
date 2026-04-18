"""Coil spring — circular wire profile swept along a helix path.

Structural type: helix sweep. Impossible with extrude/revolve alone.

Easy:   plain coil (helix sweep of circle)
Medium: + flat ground ends (cut top/bottom) + closed coil
Hard:   + variable pitch (two-section helix) + end hooks
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class CoilSpringFamily(BaseFamily):
    name = "coil_spring"

    def sample_params(self, difficulty: str, rng) -> dict:
        coil_r = rng.uniform(6, 40)        # coil radius (helix radius)
        wire_r = rng.uniform(2.0, min(5.0, max(2.1, coil_r * 0.25)))  # min 2mm for speed
        n_coils = rng.uniform(3, 6)        # limit coils for helix-sweep speed
        pitch = rng.uniform(wire_r * 2.5, wire_r * 5.0)      # pitch >= wire diameter
        height = round(pitch * n_coils, 1)

        params = {
            "coil_radius": round(coil_r, 1),
            "wire_radius": round(wire_r, 2),
            "n_coils": round(n_coils, 1),
            "pitch": round(pitch, 2),
            "height": height,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Grind flat: cut top and bottom to flatten ends
            grind_depth = round(wire_r * rng.uniform(0.3, 0.7), 2)
            params["grind_depth"] = grind_depth

        if difficulty == "hard":
            # Second (tighter) section at bottom — variable pitch
            n_coils_tight = rng.uniform(1, 3)
            pitch_tight = rng.uniform(wire_r * 2.2, max(wire_r * 2.3, pitch * 0.7))
            params["tight_coils"] = round(n_coils_tight, 1)
            params["tight_pitch"] = round(pitch_tight, 2)
            params["tight_height"] = round(pitch_tight * n_coils_tight, 2)

        # helix always spirals along global Z; restrict to XY base plane
        params["base_plane"] = "XY"
        return params

    def validate_params(self, params: dict) -> bool:
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        p = params["pitch"]
        h = params["height"]

        if wr >= cr * 0.3 or wr < 0.8:
            return False
        if p < wr * 2.2:
            return False
        if h < 10 or h > 300:
            return False

        gd = params.get("grind_depth", 0)
        if gd >= wr:
            return False

        tp = params.get("tight_pitch")
        if tp and tp < wr * 2.1:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        cr = params["coil_radius"]
        wr = params["wire_radius"]
        p = params["pitch"]
        h = params["height"]

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": True,
        }

        # Main coil: circle cross-section swept along helix
        # The circle is on XY plane at (coil_radius, 0), helix axis = Z
        ops.append(Op("transformed", {
            "offset": [cr, 0, 0],
            "rotate": [0, 0, 0],
        }))
        ops.append(Op("circle", {"radius": wr}))
        ops.append(Op("sweep", {
            "path_type": "helix",
            "path_args": {
                "pitch": p,
                "height": h,
                "radius": cr,
            },
            "isFrenet": True,
        }))

        # Hard: extra grind at top face (simulates closed/ground ends on both ends)
        # The seat-washer approach (union+cut cylinder) fails for complex helix topology.
        # Instead just grind both ends flat using box cuts.

        # Grind flat ends: box cuts at bottom (medium+) and top (hard)
        gd = params.get("grind_depth", 0)
        if gd > 0:
            cut_w = round(cr * 3, 2)
            # Cut bottom
            ops.append(Op("cut", {
                "ops": [
                    {"name": "box", "args": {
                        "length": cut_w, "width": cut_w,
                        "height": round(gd * 2, 3),
                        "centered": True,
                    }},
                ],
            }))
            # Hard: also grind top end flat
            if difficulty == "hard":
                ops.append(Op("cut", {
                    "ops": [
                        {"name": "transformed", "args": {
                            "offset": [0, 0, round(h, 3)],
                            "rotate": [0, 0, 0],
                        }},
                        {"name": "box", "args": {
                            "length": cut_w, "width": cut_w,
                            "height": round(gd * 2, 3),
                            "centered": True,
                        }},
                    ],
                }))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
