"""simple_worm_screw — cylinder with helical sweep cut.

Variants:
  bare_shaft:       smooth shaft cylinder                                  (easy)
  helix_subtract:   shaft − helix sweep (rect profile)                     (med, classic worm)
  thin_plate_worm:  same but with stepped end shoulders                    (hard, multi-step)
  shaft_two_steps:  hub + smaller shaft cylinder + helix on smaller part   (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("bare_shaft", "helix_subtract", "thin_plate_worm", "shaft_two_steps")


class SimpleWormScrewFamily(BaseFamily):
    name = "simple_worm_screw"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "bare_shaft"
        elif difficulty == "medium":
            v = "helix_subtract"
        else:
            v = str(
                rng.choice(["thin_plate_worm", "shaft_two_steps", "helix_subtract"])
            )

        r = round(float(rng.uniform(6, 14)), 1)
        h = round(float(rng.uniform(40, 80)), 1)
        pitch = round(float(rng.uniform(3, 7)), 2)
        thread_d = round(float(rng.uniform(1.5, 3.0)), 2)
        thread_w = round(float(rng.uniform(0.8, 1.6)), 2)
        shoulder_h = round(h * 0.12, 2)
        return {
            "variant": v,
            "radius": r,
            "height": h,
            "pitch": pitch,
            "thread_d": thread_d,
            "thread_w": thread_w,
            "shoulder_h": shoulder_h,
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["radius"] >= 4
            and p["height"] >= 20
            and p["pitch"] > p["thread_w"]
            and p["thread_d"] < p["radius"] - 1
        )

    def make_program(self, p):
        v = p["variant"]
        r, h, pi_ = p["radius"], p["height"], p["pitch"]
        td, tw = p["thread_d"], p["thread_w"]
        ops: list = []
        tags = {"variant": v, "rotational": True}

        if v == "bare_shaft":
            ops += [Op("circle", {"radius": r}), Op("extrude", {"distance": h})]
        elif v == "shaft_two_steps":
            # Outer hub flange (radius r*1.4) + threaded core (radius r) with helix groove
            r_hub = round(r * 1.4, 2)
            hub_h = round(h * 0.18, 2)
            core_r = round(r * 0.85, 2)
            core_h = round(h - hub_h, 2)
            ops += [
                Op("circle", {"radius": r_hub}),
                Op("extrude", {"distance": hub_h}),
                Op("workplane", {"selector": ">Z"}),
                Op("circle", {"radius": core_r}),
                Op("extrude", {"distance": core_h}),
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {"name": "center", "args": {"x": core_r, "y": 0.0}},
                            {"name": "rect", "args": {"length": tw, "width": td}},
                            {
                                "name": "sweep",
                                "args": {
                                    "path_type": "helix",
                                    "path_args": {
                                        "pitch": pi_,
                                        "height": core_h,
                                        "radius": core_r,
                                    },
                                },
                            },
                        ],
                    },
                ),
            ]
            tags["helix_cut"] = True
            tags["two_step"] = True
        else:
            # helix_subtract / thin_plate_worm: cylinder − helix sweep
            ops += [
                Op("circle", {"radius": r}),
                Op("extrude", {"distance": h}),
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {"name": "center", "args": {"x": r, "y": 0.0}},
                            {"name": "rect", "args": {"length": tw, "width": td}},
                            {
                                "name": "sweep",
                                "args": {
                                    "path_type": "helix",
                                    "path_args": {
                                        "pitch": pi_,
                                        "height": h,
                                        "radius": r,
                                    },
                                },
                            },
                        ],
                    },
                ),
            ]
            if v == "thin_plate_worm":
                # Add end shoulder steps
                sh = p["shoulder_h"]
                ops += [
                    Op("workplane", {"selector": ">Z"}),
                    Op("circle", {"radius": r * 0.7}),
                    Op("extrude", {"distance": sh}),
                ]
                tags["with_shoulder"] = True
            tags["helix_cut"] = True

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
