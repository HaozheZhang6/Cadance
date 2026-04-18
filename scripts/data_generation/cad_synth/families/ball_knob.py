"""Ball knob — spherical grip on a cylindrical stem.

Represents: machine handle knob, indexing plunger knob, control knob.
Uses the `sphere` CadQuery primitive directly.

Easy only: sphere + cylindrical stem below.
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class BallKnobFamily(BaseFamily):
    name = "ball_knob"

    def sample_params(self, difficulty: str, rng) -> dict:
        ball_r = round(rng.uniform(10, 40), 1)
        stem_r = round(rng.uniform(ball_r * 0.25, ball_r * 0.5), 1)
        stem_h = round(rng.uniform(ball_r * 0.8, ball_r * 3), 1)

        return {
            "ball_radius": ball_r,
            "stem_radius": stem_r,
            "stem_height": stem_h,
            "difficulty": difficulty,
        }

    def validate_params(self, params: dict) -> bool:
        ball_r = params["ball_radius"]
        stem_r = params["stem_radius"]
        stem_h = params["stem_height"]

        if ball_r < 8:
            return False
        if stem_r < 4:
            return False
        if stem_r >= ball_r * 0.6:
            return False
        if stem_h < 10:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ball_r = params["ball_radius"]
        stem_r = params["stem_radius"]
        stem_h = params["stem_height"]

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        # Sphere (ball) centred at origin
        ops.append(Op("sphere", {"radius": round(ball_r, 4)}))

        # Stem: cylinder pointing downward from sphere.
        # Centre of stem at (0, 0, -(ball_r + stem_h/2)).
        stem_cz = round(-(ball_r + stem_h / 2), 4)
        ops.append(Op("union", {"ops": [
            {"name": "transformed",
             "args": {"offset": [0.0, 0.0, stem_cz], "rotate": [0, 0, 0]}},
            {"name": "cylinder",
             "args": {"height": round(stem_h, 4), "radius": round(stem_r, 4)}},
        ]}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
