"""simple_torsion_spring — helix + flat tangent legs.

Variants:
  helix_only:      pure helix without legs (degenerate torsion spring)    (easy)
  short_legs:      helix_with_legs short                                  (med)
  long_legs:       helix_with_legs long                                   (hard)
  square_wire:     square cross-section instead of round                  (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("helix_only", "short_legs", "long_legs", "square_wire")


class SimpleTorsionSpringFamily(BaseFamily):
    name = "simple_torsion_spring"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "helix_only"
        elif difficulty == "medium":
            v = str(rng.choice(["short_legs", "helix_only"]))
        else:
            v = str(rng.choice(["short_legs", "long_legs", "square_wire"]))

        wd = round(float(rng.uniform(1.2, 3.0)), 2)
        cr = round(float(rng.uniform(6, 15)), 1)
        pi_ = round(wd * float(rng.uniform(1.5, 2.5)), 2)
        n = int(rng.choice([3, 4, 5, 6]))
        h = round(pi_ * n, 2)

        if v == "long_legs":
            ll = round(cr * float(rng.uniform(1.5, 2.5)), 2)
        elif v == "short_legs":
            ll = round(cr * float(rng.uniform(0.4, 0.8)), 2)
        else:
            ll = round(cr * 0.5, 2)

        return {
            "variant": v,
            "wire_d": wd,
            "coil_radius": cr,
            "pitch": pi_,
            "n_turns": n,
            "height": h,
            "leg_length": ll,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["wire_d"] >= 1
            and p["coil_radius"] > p["wire_d"]
            and p["pitch"] >= p["wire_d"] * 1.1
            and p["height"] >= 3
        )

    def make_program(self, p):
        v = p["variant"]
        wd, cr, pi_, h, ll = (
            p["wire_d"],
            p["coil_radius"],
            p["pitch"],
            p["height"],
            p["leg_length"],
        )
        ops: list = []
        tags = {"variant": v, "helical": True}

        if v == "square_wire":
            profile = Op("rect", {"length": wd, "width": wd})
        else:
            profile = Op("circle", {"radius": wd / 2})

        ops.append(Op("center", {"x": cr, "y": 0.0}))
        ops.append(profile)
        if v == "helix_only":
            ops.append(
                Op(
                    "sweep",
                    {
                        "path_type": "helix",
                        "path_args": {"pitch": pi_, "height": h, "radius": cr},
                    },
                )
            )
        else:
            ops.append(
                Op(
                    "sweep",
                    {
                        "path_type": "helix_with_legs",
                        "path_args": {
                            "pitch": pi_,
                            "height": h,
                            "radius": cr,
                            "leg_length": ll,
                        },
                    },
                )
            )
            tags["with_legs"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
