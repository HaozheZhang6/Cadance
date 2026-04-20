"""Pipe flange family — square/rectangular plate with center bore + bolt holes.

Typical use: pipe connections, valve flanges, duct fittings.
Easy:   plate + center through-hole
Medium: plate + center bore + 4 corner bolt holes + fillet edges
Hard:   plate + raised boss around bore + bolt holes + chamfer
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class PipeFlangeFamily(BaseFamily):
    """Parametric pipe flange: plate with central bore and corner bolt holes."""

    name = "pipe_flange"
    standard = "ASME B16.5"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a pipe flange."""
        side = rng.uniform(60, 200)  # plate is roughly square
        aspect = rng.uniform(0.7, 1.3)
        length = round(side, 1)
        width = round(side * aspect, 1)
        thickness = rng.uniform(8, 30)
        bore_r = rng.uniform(10, min(length, width) / 3)

        params = {
            "length": length,
            "width": width,
            "thickness": round(thickness, 1),
            "bore_diameter": round(bore_r * 2, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # Corner bolt holes
            max_hd = min(8.0, (min(length, width) / 2 - bore_r - 5) * 0.5)
            hd = rng.uniform(3.0, max(3.5, max_hd))
            inset = rng.uniform(hd / 2 + 5, min(length, width) / 2 - hd / 2 - 3)
            params["bolt_diameter"] = round(hd, 1)
            params["bolt_inset"] = round(inset, 1)  # from plate center to bolt center
            # Fillet on vertical edges
            max_fr = min(thickness / 4, 3.0)
            if max_fr >= 0.5:
                params["fillet_radius"] = round(rng.uniform(0.5, max_fr), 1)

        if difficulty == "hard":
            # Raised boss around bore
            boss_r = rng.uniform(bore_r + 3, bore_r + 15)
            boss_h = rng.uniform(3, min(15, thickness * 0.6))
            params["boss_radius"] = round(boss_r, 1)
            params["boss_height"] = round(boss_h, 1)
            cl = rng.uniform(0.5, min(2.5, thickness / 6))
            params["chamfer_length"] = round(cl, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        l, w = params["length"], params["width"]
        t = params["thickness"]
        bd = params["bore_diameter"]

        if t < 5 or t > l or t > w:
            return False
        bore_r = bd / 2
        if bore_r >= min(l, w) / 3:
            return False
        if bore_r < 3:
            return False

        hd = params.get("bolt_diameter")
        inset = params.get("bolt_inset", 0)
        if hd is not None:
            if inset - hd / 2 < bore_r + 3:
                return False
            if inset + hd / 2 > min(l, w) / 2 - 2:
                return False

        boss_r = params.get("boss_radius")
        if boss_r is not None:
            if boss_r >= min(l, w) / 2 - 3:
                return False
            if boss_r <= bore_r + 1:
                return False
            boss_h = params.get("boss_height", 0)
            if boss_h >= t:
                return False

        fr = params.get("fillet_radius")
        if fr is not None and fr >= t / 4:
            return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= t / 6:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        l, w = params["length"], params["width"]
        t = params["thickness"]
        bd = params["bore_diameter"]

        ops = []
        tags = {
            "has_hole": True,
            "has_fillet": False,
            "has_chamfer": False,
            "has_boss": False,
            "pattern_like": False,
        }

        # Base plate
        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Fillet vertical edges first (before adding features)
        fr = params.get("fillet_radius")
        if fr is not None:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Center bore (through hole)
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": bd}))

        # Corner bolt holes (medium/hard)
        hd = params.get("bolt_diameter")
        inset = params.get("bolt_inset", 0)
        if hd is not None:
            tags["pattern_like"] = True
            corners = [
                (inset - l / 2, inset - w / 2),
                (inset - l / 2, w / 2 - inset),
                (l / 2 - inset, inset - w / 2),
                (l / 2 - inset, w / 2 - inset),
            ]
            corners = [(round(x, 4), round(y, 4)) for x, y in corners]
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("pushPoints", {"points": corners}))
            ops.append(Op("hole", {"diameter": hd}))

        # Raised boss around bore (hard)
        boss_r = params.get("boss_radius")
        boss_h = params.get("boss_height")
        if boss_r is not None and boss_h is not None:
            tags["has_boss"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": boss_r}))
            ops.append(Op("extrude", {"distance": boss_h}))
            # Re-bore through the boss to maintain clean through-hole
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        # Chamfer top edges of plate (hard)
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
