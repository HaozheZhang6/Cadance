"""Enclosure family — hollow rectangular shell, open top.

Geometry: box → shell (open top face).  Medium/hard add mounting holes on the
bottom floor and fillets on inner bottom edges.
"""


from ..pipeline.builder import Op, Program
from .base import BaseFamily


class EnclosureFamily(BaseFamily):
    """Parametric rectangular enclosure: hollow shell with open top."""

    name = "enclosure"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for an enclosure at given difficulty."""
        length = rng.uniform(60, 200)
        width = rng.uniform(40, 150)
        # Shallow tray — height << footprint so camera sees into open top
        height = rng.uniform(12, min(40, length * 0.3, width * 0.4))
        # Wall thickness: constrained to < min(length, width, height) / 6
        max_wall = min(length, width, height) / 6.0
        wall = rng.uniform(1.5, min(4.0, max(1.6, max_wall * 0.8)))

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "height": round(height, 1),
            "wall": round(wall, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_fr = min(wall * 0.8, 3.0)
            if max_fr >= 0.5:
                params["fillet_radius"] = round(rng.uniform(0.5, max_fr), 1)

        if difficulty == "hard":
            # Mounting holes on bottom floor (inside the enclosure)
            max_hd = min(wall * 0.7, 4.0)
            if max_hd >= 1.5:
                params["hole_diameter"] = round(rng.uniform(1.5, max_hd), 1)
                # 2x2 grid of holes with margin
                params["hole_nx"] = int(rng.choice([2, 2, 2, 3]))
                params["hole_ny"] = int(rng.choice([2, 2, 3]))
                inner_l = length - 2 * wall
                inner_w = width - 2 * wall
                margin = max(5.0, min(inner_l, inner_w) * 0.15)
                nx = params["hole_nx"]
                ny = params["hole_ny"]
                params["hole_spacing_x"] = (
                    round((inner_l - 2 * margin) / max(1, nx - 1), 1) if nx > 1 else 0
                )
                params["hole_spacing_y"] = (
                    round((inner_w - 2 * margin) / max(1, ny - 1), 1) if ny > 1 else 0
                )

        return params

    def validate_params(self, params: dict) -> bool:
        """Validate enclosure constraints."""
        l, w, h = params["length"], params["width"], params["height"]
        wall = params["wall"]

        if wall >= min(l, w, h) / 6:
            return False
        if wall < 1.2:
            return False
        # Shell needs enough interior room
        if l - 2 * wall < 5 or w - 2 * wall < 5 or h - wall < 5:
            return False

        fr = params.get("fillet_radius")
        if fr is not None and fr >= wall:
            return False

        hd = params.get("hole_diameter")
        if hd is not None and hd >= wall:
            return False

        nx = params.get("hole_nx", 1)
        ny = params.get("hole_ny", 1)
        if nx > 1:
            sx = params.get("hole_spacing_x", 0)
            if sx <= 0:
                return False
        if ny > 1:
            sy = params.get("hole_spacing_y", 0)
            if sy <= 0:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        """Build program for enclosure."""
        difficulty = params.get("difficulty", "easy")
        l, w, h = params["length"], params["width"], params["height"]
        wall = params["wall"]

        ops = []
        tags = {
            "has_hole": False,
            "has_fillet": False,
            "has_shell": True,
            "has_chamfer": False,
            "enclosure": True,
        }

        # Shallow tray — open top so camera at 35° elevation sees inside
        ops.append(Op("box", {"length": l, "width": w, "height": h}))
        ops.append(Op("faces", {"selector": ">Z"}))
        ops.append(Op("shell", {"thickness": -wall}))

        # Fillet bottom outer edges (medium/hard)
        fr = params.get("fillet_radius")
        if fr is not None:
            tags["has_fillet"] = True
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("edges", {"selector": "<Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Mounting holes on bottom face (hard)
        hd = params.get("hole_diameter")
        if hd is not None:
            tags["has_hole"] = True
            nx = params.get("hole_nx", 2)
            ny = params.get("hole_ny", 2)
            sx = params.get("hole_spacing_x", 0) if nx > 1 else 1
            sy = params.get("hole_spacing_y", 0) if ny > 1 else 1
            # Select bottom face, use rarray for pattern
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(
                Op(
                    "rarray",
                    {
                        "xSpacing": sx if nx > 1 else 1,
                        "ySpacing": sy if ny > 1 else 1,
                        "xCount": nx,
                        "yCount": ny,
                    },
                )
            )
            ops.append(Op("hole", {"diameter": hd}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
