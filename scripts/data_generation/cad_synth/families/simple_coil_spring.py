"""simple_coil_spring — helical sweep with simple cross-section profiles.

Variants:
  circle_helix:    circular cross-section sweep along helix              (easy default)
  square_helix:    square cross-section helix (compression spring)       (med)
  helix_with_legs: helix + straight tangent leg ends                     (hard, uses helix_with_legs)
  rect_helix:      rectangular profile sweep                             (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("circle_helix", "square_helix", "helix_with_legs", "rect_helix")


class SimpleCoilSpringFamily(BaseFamily):
    name = "simple_coil_spring"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "circle_helix"
        elif difficulty == "medium":
            v = str(rng.choice(["circle_helix", "square_helix"]))
        else:
            v = str(rng.choice(VARIANTS))

        wire_d = round(float(rng.uniform(1.5, 4.0)), 2)
        coil_r = round(float(rng.uniform(8, 22)), 1)
        pitch = round(wire_d * float(rng.uniform(1.6, 3.0)), 2)
        n_turns = int(rng.choice([4, 5, 6, 7, 8, 10]))
        height = round(pitch * n_turns, 2)
        leg_len = round(coil_r * 0.7, 2)
        return {
            "variant": v,
            "wire_d": wire_d,
            "coil_radius": coil_r,
            "pitch": pitch,
            "n_turns": n_turns,
            "height": height,
            "leg_length": leg_len,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["wire_d"] >= 1
            and p["coil_radius"] > p["wire_d"]
            and p["pitch"] >= p["wire_d"] * 1.2
            and p["height"] >= 4
        )

    def make_program(self, p):
        v = p["variant"]
        wd, cr, pi_, h = p["wire_d"], p["coil_radius"], p["pitch"], p["height"]
        ops: list = []
        tags = {"variant": v, "helical": True}

        # Profile placement: shift the cross-section by coil_r along X to make it sweep on the helix.
        # The sweep path starts at (cr, 0, 0).
        if v == "circle_helix":
            ops += [
                Op("center", {"x": cr, "y": 0.0}),
                Op("circle", {"radius": wd / 2}),
                Op(
                    "sweep",
                    {
                        "path_type": "helix",
                        "path_args": {"pitch": pi_, "height": h, "radius": cr},
                    },
                ),
            ]
        elif v == "square_helix":
            ops += [
                Op("center", {"x": cr, "y": 0.0}),
                Op("rect", {"length": wd, "width": wd}),
                Op(
                    "sweep",
                    {
                        "path_type": "helix",
                        "path_args": {"pitch": pi_, "height": h, "radius": cr},
                    },
                ),
            ]
        elif v == "rect_helix":
            ops += [
                Op("center", {"x": cr, "y": 0.0}),
                Op("rect", {"length": wd * 1.6, "width": wd}),
                Op(
                    "sweep",
                    {
                        "path_type": "helix",
                        "path_args": {"pitch": pi_, "height": h, "radius": cr},
                    },
                ),
            ]
        else:  # helix_with_legs
            ops += [
                Op("center", {"x": cr, "y": 0.0}),
                Op("circle", {"radius": wd / 2}),
                Op(
                    "sweep",
                    {
                        "path_type": "helix_with_legs",
                        "path_args": {
                            "pitch": pi_,
                            "height": h,
                            "radius": cr,
                            "leg_length": p["leg_length"],
                        },
                    },
                ),
            ]
            tags["with_legs"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
