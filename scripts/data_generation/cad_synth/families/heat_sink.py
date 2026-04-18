"""Heat sink family — rectangular base plate with parallel cooling fins.

Typical use: PCB heat sinks, power electronics cooling, motor controllers.
Easy:   base + 4–8 straight fins
Medium: base + more fins + chamfer on fin tops
Hard:   base + fins + mounting holes on base
"""

from .base import BaseFamily
from ..pipeline.builder import Op, Program


class HeatSinkFamily(BaseFamily):
    """Parametric heat sink: plate with extruded fin array."""

    name = "heat_sink"

    def sample_params(self, difficulty: str, rng) -> dict:
        """Sample params for a heat sink."""
        base_l = rng.uniform(40, 150)
        base_w = rng.uniform(30, 120)
        base_t = rng.uniform(3, 8)

        # Fins run along the length direction (X)
        n_fins = int(rng.choice([4, 5, 6, 7, 8]))
        fin_h  = rng.uniform(8, 40)
        # Fin thickness: must leave gaps between fins
        max_fin_t = (base_w - 4) / (n_fins * 2)  # half gap, half fin
        fin_t = rng.uniform(1.0, max(1.2, max_fin_t * 0.7))
        # spacing = center-to-center; total span = spacing*(n-1)+fin_t must fit in base_w
        fin_spacing = (base_w - 4 - fin_t) / max(1, n_fins - 1) if n_fins > 1 else base_w

        params = {
            "base_length": round(base_l, 1),
            "base_width": round(base_w, 1),
            "base_thickness": round(base_t, 1),
            "n_fins": n_fins,
            "fin_height": round(fin_h, 1),
            "fin_thickness": round(fin_t, 1),
            "fin_spacing": round(fin_spacing, 2),
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            chamfer = rng.uniform(0.3, min(1.5, fin_t * 0.4))
            params["chamfer_length"] = round(chamfer, 1)

        if difficulty == "hard":
            # Mounting holes on the base (4 corners)
            max_hd = min(base_t * 0.8, 4.0)
            if max_hd >= 1.5:
                hd = rng.uniform(1.5, max_hd)
                margin = hd / 2 + 3
                params["hole_diameter"] = round(hd, 1)
                params["hole_inset_x"] = round(
                    rng.uniform(margin, max(margin + 1, base_l / 2 - margin)), 1
                )
                params["hole_inset_y"] = round(
                    rng.uniform(margin, max(margin + 1, base_w / 2 - margin)), 1
                )

        return params

    def validate_params(self, params: dict) -> bool:
        bl = params["base_length"]
        bw = params["base_width"]
        bt = params["base_thickness"]
        nf = params["n_fins"]
        fh = params["fin_height"]
        ft = params["fin_thickness"]
        fs = params["fin_spacing"]

        if bt < 2 or fh < 4 or ft < 0.8:
            return False
        if nf < 2:
            return False
        # Fins must fit within base width (total fin span + gaps)
        total_fin_span = fs * (nf - 1) + ft
        if total_fin_span > bw - 2 + 0.5:  # 0.5mm rounding tolerance
            return False
        # Fin depth must not exceed base length
        if bl < 10:
            return False

        cl = params.get("chamfer_length")
        if cl is not None and cl >= ft / 2:
            return False

        hd = params.get("hole_diameter")
        if hd is not None:
            ix = params.get("hole_inset_x", 0)
            iy = params.get("hole_inset_y", 0)
            if ix - hd / 2 < 1 or iy - hd / 2 < 1:
                return False
            if ix + hd / 2 > bl / 2 or iy + hd / 2 > bw / 2:
                return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        bl = params["base_length"]
        bw = params["base_width"]
        bt = params["base_thickness"]
        nf = params["n_fins"]
        fh = params["fin_height"]
        ft = params["fin_thickness"]
        fs = params["fin_spacing"]

        ops = []
        tags = {
            "has_hole": False,
            "has_chamfer": False,
            "has_fillet": False,
            "pattern_like": True,
        }

        # Base plate
        ops.append(Op("box", {"length": bl, "width": bw, "height": bt}))

        # Fins: rarray along Y (width direction), each fin = thin rect extruded up
        # rarray(xSpacing, ySpacing, xCount, yCount)
        # We want 1 row of nf fins along Y
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("rarray", {
            "xSpacing": 1,      # xCount=1, so spacing doesn't matter
            "ySpacing": fs,
            "xCount": 1,
            "yCount": nf,
        }))
        # Each fin: thin in Y, spans full length in X (minus small margin)
        ops.append(Op("rect", {"length": bl - 2, "width": ft}))
        ops.append(Op("extrude", {"distance": fh}))

        # Chamfer top edges of fins (medium/hard)
        cl = params.get("chamfer_length")
        if cl is not None:
            tags["has_chamfer"] = True
            ops.append(Op("faces", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Corner mounting holes through base (hard)
        hd = params.get("hole_diameter")
        if hd is not None:
            tags["has_hole"] = True
            ix = params["hole_inset_x"]
            iy = params["hole_inset_y"]
            corners = [
                ( ix - bl/2,  iy - bw/2),
                ( ix - bl/2,  bw/2 - iy),
                ( bl/2 - ix,  iy - bw/2),
                ( bl/2 - ix,  bw/2 - iy),
            ]
            corners = [(round(x, 4), round(y, 4)) for x, y in corners]
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("pushPoints", {"points": corners}))
            ops.append(Op("hole", {"diameter": hd}))

        return Program(
            family=self.name, difficulty=difficulty,
            params=params, ops=ops, feature_tags=tags,
        )
