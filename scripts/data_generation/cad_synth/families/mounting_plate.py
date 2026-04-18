"""Mounting plate family — rectangular plate with optional holes/fillets."""


from ..pipeline.builder import Op, Program
from .base import BaseFamily


class MountingPlateFamily(BaseFamily):
    """Parametric mounting plate: rect base + optional corner holes + fillet."""

    name = "mounting_plate"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a mounting plate at given difficulty."""
        length = rng.uniform(30, 200)
        width = rng.uniform(30, 200)
        thickness = rng.uniform(3, 20)

        params = {
            "length": round(length, 1),
            "width": round(width, 1),
            "thickness": round(thickness, 1),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            max_hole_d = min(length, width) / 3
            hole_d = rng.uniform(2, max(2.5, max_hole_d * 0.6))
            params["hole_diameter"] = round(hole_d, 1)
            # Inset from edges
            margin = hole_d / 2 + 3
            params["hole_inset_x"] = round(
                rng.uniform(margin, max(margin + 1, length / 2 - margin)), 1
            )
            params["hole_inset_y"] = round(
                rng.uniform(margin, max(margin + 1, width / 2 - margin)), 1
            )

        if difficulty == "medium":
            params["fillet_radius"] = round(
                rng.uniform(0.5, min(3.0, thickness / 2 - 0.1)), 1
            )

        if difficulty == "hard":
            params["fillet_radius"] = round(
                rng.uniform(0.5, min(3.0, thickness / 2 - 0.1)), 1
            )
            params["chamfer_length"] = round(
                rng.uniform(0.3, min(2.0, thickness / 3)), 1
            )
            # Center slot
            slot_w = rng.uniform(3, min(15, width * 0.4))
            slot_l = rng.uniform(5, min(40, length * 0.5))
            params["slot_width"] = round(slot_w, 1)
            params["slot_length"] = round(slot_l, 1)

        return params

    def validate_params(self, params: dict) -> bool:
        """Validate mounting plate constraints."""
        l, w, t = params["length"], params["width"], params["thickness"]
        if t < 3:
            return False
        if l < 10 or w < 10:
            return False

        hd = params.get("hole_diameter")
        if hd is not None:
            if hd >= min(l, w) / 3:
                return False
            ix = params.get("hole_inset_x", 0)
            iy = params.get("hole_inset_y", 0)
            if ix - hd / 2 < 1 or iy - hd / 2 < 1:
                return False
            if ix + hd / 2 > l / 2 or iy + hd / 2 > w / 2:
                return False

        fr = params.get("fillet_radius")
        if fr is not None and fr >= t / 2:
            return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= t / 3:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        """Build program for mounting plate."""
        difficulty = params.get("difficulty", "easy")
        ops = []
        tags = {
            "has_hole": False,
            "has_fillet": False,
            "has_chamfer": False,
            "has_slot": False,
            "pattern_like": False,
        }

        # Base plate
        ops.append(
            Op(
                "box",
                {
                    "length": params["length"],
                    "width": params["width"],
                    "height": params["thickness"],
                },
            )
        )

        # Fillet vertical edges FIRST (before holes/slots break topology)
        fr = params.get("fillet_radius")
        if fr is not None:
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        # Corner holes (medium/hard)
        hd = params.get("hole_diameter")
        if hd is not None:
            tags["has_hole"] = True
            tags["pattern_like"] = True
            ix = params["hole_inset_x"]
            iy = params["hole_inset_y"]
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            corners = [
                (ix - params["length"] / 2, iy - params["width"] / 2),
                (ix - params["length"] / 2, params["width"] / 2 - iy),
                (params["length"] / 2 - ix, iy - params["width"] / 2),
                (params["length"] / 2 - ix, params["width"] / 2 - iy),
            ]
            corners = [(round(x, 4), round(y, 4)) for x, y in corners]
            ops.append(Op("pushPoints", {"points": corners}))
            ops.append(Op("hole", {"diameter": hd}))

        # Center slot (hard)
        sl = params.get("slot_length")
        sw = params.get("slot_width")
        if sl is not None and sw is not None:
            tags["has_slot"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("rect", {"length": sl, "width": sw}))
            ops.append(Op("cutThruAll", {}))

        # Chamfer top edges (hard) — use >Z face edges
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
