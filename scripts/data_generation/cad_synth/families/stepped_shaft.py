"""Stepped shaft family — coaxial cylinders of decreasing diameter.

Typical use: motor shafts, transmission shafts, spindles.
Easy:   2 sections
Medium: 3 sections + chamfer on tip
Hard:   4 sections + chamfer + through center bore (making it a stepped bushing)
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class SteppedShaftFamily(BaseFamily):
    """Parametric stepped shaft: stacked coaxial cylinders."""

    name = "stepped_shaft"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a stepped shaft."""
        # Base (largest) section
        r1 = rng.uniform(8, 40)
        h1 = rng.uniform(5, 30)

        # Each successive step: smaller radius, variable height
        r2 = rng.uniform(r1 * 0.4, r1 * 0.8)
        h2 = rng.uniform(10, 60)

        params = {
            "r1": round(r1, 1), "h1": round(h1, 1),
            "r2": round(r2, 1), "h2": round(h2, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            r3 = rng.uniform(r2 * 0.4, r2 * 0.85)
            h3 = rng.uniform(5, 30)
            params["r3"] = round(r3, 1)
            params["h3"] = round(h3, 1)
            chamfer = rng.uniform(0.3, min(2.0, r3 * 0.2))
            params["chamfer_length"] = round(chamfer, 1)

        if difficulty == "hard":
            r4 = rng.uniform(r3 * 0.4, r3 * 0.85)
            h4 = rng.uniform(5, 20)
            params["r4"] = round(r4, 1)
            params["h4"] = round(h4, 1)
            # Through bore (makes it a bushing)
            bore_r = rng.uniform(1.0, max(1.1, min(r4 * 0.6, 8.0)))
            params["bore_diameter"] = round(bore_r * 2, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r1, r2 = params["r1"], params["r2"]
        if r2 >= r1 or r1 < 3 or r2 < 1.5:
            return False
        if params["h1"] < 2 or params["h2"] < 2:
            return False

        r3 = params.get("r3")
        if r3 is not None:
            if r3 >= r2 or r3 < 1.0:
                return False
            if params.get("h3", 0) < 2:
                return False
            cl = params.get("chamfer_length", 0)
            if cl >= r3:
                return False

        r4 = params.get("r4")
        if r4 is not None:
            if r4 >= (r3 or r2) or r4 < 0.5:
                return False
            bd = params.get("bore_diameter", 0)
            if bd >= r4 * 2:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        ops = []
        tags = {
            "has_hole": False,
            "has_chamfer": False,
            "has_fillet": False,
            "multi_stage": True,
        }

        # Section 1 — base (widest)
        ops.append(Op("cylinder", {"height": params["h1"], "radius": params["r1"]}))

        # Section 2
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": params["r2"]}))
        ops.append(Op("extrude", {"distance": params["h2"]}))

        # Section 3 (medium/hard)
        if "r3" in params:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": params["r3"]}))
            ops.append(Op("extrude", {"distance": params["h3"]}))

        # Section 4 (hard)
        if "r4" in params:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": params["r4"]}))
            ops.append(Op("extrude", {"distance": params["h4"]}))

        # Chamfer on the tip top edge (medium/hard)
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Through bore on base face (hard)
        bd = params.get("bore_diameter")
        if bd is not None:
            tags["has_hole"] = True
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        return Program(
            family=self.name, difficulty=difficulty,
            params=params, ops=ops, feature_tags=tags,
        )
