"""Vented panel family — flat plate with a regular array of ventilation openings.

Easy:   rectangular holes (rarray)
Medium: round holes + chamfer on plate edges
Hard:   rectangular slots + chamfer
"""


from ..pipeline.builder import Op, Program
from .base import BaseFamily


class VentedPanelFamily(BaseFamily):
    """Parametric vented panel: flat plate with regular hole/slot array."""

    name = "vented_panel"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a vented panel at given difficulty."""
        length = rng.uniform(80, 300)
        width = rng.uniform(50, 200)
        thickness = rng.uniform(2.0, 10.0)

        # Margin from plate edge to nearest hole center
        margin = max(8.0, min(length, width) * 0.1)

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "thickness": round(thickness, 1),
            "margin": round(margin, 1),
            "difficulty": difficulty,
        }

        if difficulty == "easy":
            # Round holes
            nx = int(rng.choice([3, 4, 5]))
            ny = int(rng.choice([2, 3, 4]))
            max_hole_d = min(
                (length - 2 * margin) / (nx + 0.5),
                (width - 2 * margin) / (ny + 0.5),
                12.0,
            )
            hole_d = rng.uniform(3.0, max(3.5, max_hole_d * 0.7))
            spacing_x = (length - 2 * margin) / max(1, nx - 1) if nx > 1 else length
            spacing_y = (width - 2 * margin) / max(1, ny - 1) if ny > 1 else width
            params.update(
                {
                    "hole_diameter": round(hole_d, 1),
                    "nx": nx,
                    "ny": ny,
                    "spacing_x": round(spacing_x, 2),
                    "spacing_y": round(spacing_y, 2),
                }
            )

        elif difficulty == "medium":
            # Round holes + plate edge chamfer
            nx = int(rng.choice([4, 5, 6]))
            ny = int(rng.choice([3, 4, 5]))
            max_hole_d = min(
                (length - 2 * margin) / (nx + 0.5),
                (width - 2 * margin) / (ny + 0.5),
                10.0,
            )
            hole_d = rng.uniform(3.0, max(3.5, max_hole_d * 0.65))
            spacing_x = (length - 2 * margin) / max(1, nx - 1) if nx > 1 else length
            spacing_y = (width - 2 * margin) / max(1, ny - 1) if ny > 1 else width
            chamfer = rng.uniform(0.5, min(2.0, thickness / 3))
            params.update(
                {
                    "hole_diameter": round(hole_d, 1),
                    "nx": nx,
                    "ny": ny,
                    "spacing_x": round(spacing_x, 2),
                    "spacing_y": round(spacing_y, 2),
                    "chamfer_length": round(chamfer, 1),
                }
            )

        else:  # hard — rectangular slots
            nx = int(rng.choice([3, 4, 5]))
            ny = int(rng.choice([2, 3]))
            slot_h = rng.uniform(5.0, min(25.0, (width - 2 * margin) * 0.6))
            slot_w = rng.uniform(3.0, min(15.0, (length - 2 * margin) / (nx + 0.5)))
            spacing_x = (length - 2 * margin) / max(1, nx - 1) if nx > 1 else length
            spacing_y = (width - 2 * margin) / max(1, ny - 1) if ny > 1 else width
            chamfer = rng.uniform(0.5, min(2.0, thickness / 3))
            params.update(
                {
                    "slot_width": round(slot_w, 1),
                    "slot_height": round(slot_h, 1),
                    "nx": nx,
                    "ny": ny,
                    "spacing_x": round(spacing_x, 2),
                    "spacing_y": round(spacing_y, 2),
                    "chamfer_length": round(chamfer, 1),
                }
            )

        return params

    def validate_params(self, params: dict) -> bool:
        """Validate vented panel constraints."""
        l = params["length"]
        w = params["width"]
        t = params["thickness"]
        m = params["margin"]
        nx = params.get("nx", 1)
        ny = params.get("ny", 1)
        sx = params.get("spacing_x", 0)
        sy = params.get("spacing_y", 0)

        if t < 1.5:
            return False
        if m < 5:
            return False

        # Pattern fits within plate (0.5 mm tolerance for rounding)
        if nx > 1 and sx * (nx - 1) > l - 2 * m + 0.5:
            return False
        if ny > 1 and sy * (ny - 1) > w - 2 * m + 0.5:
            return False

        hd = params.get("hole_diameter")
        if hd is not None:
            if hd >= t * 1.5 or hd <= 1:
                return False
            # Holes don't overlap in X or Y
            if nx > 1 and hd >= sx * 0.85:
                return False
            if ny > 1 and hd >= sy * 0.85:
                return False

        sl_w = params.get("slot_width")
        sl_h = params.get("slot_height")
        if sl_w is not None:
            if sl_w <= 1 or sl_h <= 1:
                return False
            if nx > 1 and sl_w >= sx * 0.85:
                return False
            if ny > 1 and sl_h >= sy * 0.85:
                return False
            if sl_h >= w - 2 * m:
                return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= t / 3:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        """Build program for vented panel."""
        difficulty = params.get("difficulty", "easy")
        l = params["length"]
        w = params["width"]
        t = params["thickness"]
        nx = params.get("nx", 3)
        ny = params.get("ny", 2)
        sx = params.get("spacing_x", 1)
        sy = params.get("spacing_y", 1)

        ops = []
        tags = {
            "has_hole": False,
            "has_slot": False,
            "has_chamfer": False,
            "pattern_like": True,
        }

        # Base plate
        ops.append(Op("box", {"length": l, "width": w, "height": t}))

        # Chamfer plate top edges (medium/hard) — BEFORE vents for clean 4-edge face
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Ventilation openings on top face
        ops.append(Op("workplane", {"selector": ">Z"}))

        hd = params.get("hole_diameter")
        sl_w = params.get("slot_width")
        sl_h = params.get("slot_height")

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

        if hd is not None:
            # Round holes
            tags["has_hole"] = True
            ops.append(Op("hole", {"diameter": hd}))
        elif sl_w is not None and sl_h is not None:
            # Rectangular slots
            tags["has_slot"] = True
            ops.append(Op("rect", {"length": sl_w, "width": sl_h}))
            ops.append(Op("cutThruAll", {}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
