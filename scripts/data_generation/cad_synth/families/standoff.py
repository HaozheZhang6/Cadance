"""Standoff / spacer family — cylindrical spacer with through bore.

Typical use: PCB standoffs, fastener spacers, shaft collars.
Easy:   cylinder + through bore
Medium: + chamfer on both ends
Hard:   + hex outer profile approximated as short hexagonal prism base
        (using a regular polygon approximation: circle with facets via loft trick)
        — simplified to: cylinder + chamfer + knurled approx (stepped outer)
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class StandoffFamily(BaseFamily):
    """Parametric cylindrical standoff with through bore."""

    name = "standoff"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a standoff."""
        outer_r = rng.uniform(3, 20)
        height  = rng.uniform(5, 60)
        # Inner bore: must leave wall thickness ≥ 1mm
        max_bore_r = outer_r - 1.0
        bore_r = rng.uniform(1.0, max(1.1, max_bore_r * 0.8))

        params = {
            "outer_radius": round(outer_r, 1),
            "height": round(height, 1),
            "bore_diameter": round(bore_r * 2, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_cl = min(outer_r * 0.15, 2.0)
            if max_cl >= 0.3:
                params["chamfer_length"] = round(rng.uniform(0.3, max_cl), 1)

        if difficulty == "hard":
            # Stepped outer profile (simulates hex or knurled grip section)
            # Add a wider flange at the base
            flange_r = rng.uniform(outer_r + 2, outer_r + 8)
            flange_h = rng.uniform(2, max(2.5, min(height * 0.3, 8)))
            params["flange_radius"] = round(flange_r, 1)
            params["flange_height"] = round(flange_h, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r = params["outer_radius"]
        h = params["height"]
        bd = params["bore_diameter"]

        if r < 2 or h < 3:
            return False
        if bd / 2 >= r - 0.8:
            return False
        if bd < 1.0:
            return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= r * 0.2:
            return False

        fr = params.get("flange_radius")
        if fr is not None:
            fh = params.get("flange_height", 0)
            if fr <= r + 1:
                return False
            if fh >= h:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r = params["outer_radius"]
        h = params["height"]
        bd = params["bore_diameter"]

        ops = []
        tags = {
            "has_hole": True,
            "has_chamfer": False,
            "has_fillet": False,
        }

        # Base flange (hard) — built first so standoff sits on top
        fr = params.get("flange_radius")
        fh = params.get("flange_height")
        if fr is not None and fh is not None:
            ops.append(Op("cylinder", {"height": fh, "radius": fr}))
            # Build standoff body on top of flange
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": r}))
            ops.append(Op("extrude", {"distance": h - fh}))
        else:
            ops.append(Op("cylinder", {"height": h, "radius": r}))

        # Through bore
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": bd}))

        # Chamfer top and bottom ends (medium/hard)
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        return Program(
            family=self.name, difficulty=difficulty,
            params=params, ops=ops, feature_tags=tags,
        )
