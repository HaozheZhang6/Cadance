"""simple_step_solid — staircase block via N stacked rectangular sketches+extrudes.

Multi-extrude composition (3+ sketch+extrude) inspired by Fusion360 designs.

Variants:
  two_step:       two stacked decreasing-footprint blocks               (easy)
  three_step:     three stacked blocks (Aztec pyramid)                  (med)
  four_step:      four stacked blocks                                   (hard)
  asymmetric:     three blocks each shifted in X/Y                      (hard)
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

VARIANTS = ("two_step", "three_step", "four_step", "asymmetric")


class SimpleStepSolidFamily(BaseFamily):
    name = "simple_step_solid"
    standard = "N/A"

    def sample_params(self, difficulty, rng):
        if difficulty == "easy":
            v = "two_step"
        elif difficulty == "medium":
            v = "three_step"
        else:
            v = str(rng.choice(["four_step", "asymmetric"]))

        L = round(float(rng.uniform(40, 90)), 1)
        W = round(float(rng.uniform(30, 70)), 1)
        h_step = round(float(rng.uniform(5, 12)), 1)
        shrink = float(rng.uniform(0.65, 0.85))
        return {
            "variant": v,
            "base_length": L,
            "base_width": W,
            "step_height": h_step,
            "shrink_ratio": shrink,
            "shift_x": round(float(rng.uniform(-3, 3)), 1),
            "shift_y": round(float(rng.uniform(-3, 3)), 1),
            "difficulty": difficulty,
        }

    def validate_params(self, p):
        return (
            p["base_length"] >= 20
            and p["base_width"] >= 15
            and 0.5 <= p["shrink_ratio"] < 1
            and p["step_height"] >= 2
        )

    def make_program(self, p):
        v = p["variant"]
        L, W, h, s = (
            p["base_length"],
            p["base_width"],
            p["step_height"],
            p["shrink_ratio"],
        )
        n = {"two_step": 2, "three_step": 3, "four_step": 4, "asymmetric": 3}[v]
        ops: list = []
        tags = {"variant": v, "n_steps": n}

        Lc, Wc = L, W
        for i in range(n):
            if i == 0:
                ops += [
                    Op("rect", {"length": Lc, "width": Wc}),
                    Op("extrude", {"distance": h}),
                ]
            else:
                if v == "asymmetric":
                    ops += [
                        Op("workplane", {"selector": ">Z"}),
                        Op("center", {"x": p["shift_x"] * i, "y": p["shift_y"] * i}),
                        Op("rect", {"length": Lc, "width": Wc}),
                        Op("extrude", {"distance": h}),
                    ]
                else:
                    ops += [
                        Op("workplane", {"selector": ">Z"}),
                        Op("rect", {"length": Lc, "width": Wc}),
                        Op("extrude", {"distance": h}),
                    ]
            Lc = round(Lc * s, 2)
            Wc = round(Wc * s, 2)

        return Program(
            family=self.name,
            difficulty=p["difficulty"],
            params=p,
            ops=ops,
            feature_tags=tags,
        )
