"""T-slot rail — ISO 299 slot widths, complex polyline cross-section + extrude.

Structural type: non-rectangular prismatic extrusion. Completely different topology.
The T-slot groove runs along the length, making it impossible to mistake for a box+hole.

Easy:   T-slot profile (one slot) extruded
Medium: + 2 slots (4-way) + mounting holes on ends
Hard:   + 4-way slot + lightening pockets
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class TSlotRailFamily(BaseFamily):
    name = "t_slot_rail"
    standard = "DIN 650"

    # ISO 299 T-slot widths → mating bolt + rail size (mm)
    # slot_w: ISO 299 nominal; size: square rail cross-section
    _ISO299 = [
        (8, "M8", 20),
        (10, "M10", 25),
        (12, "M12", 30),
        (16, "M16", 40),
        (18, "M16", 45),
        (20, "M20", 50),
        (24, "M24", 60),
        (28, "M24", 70),
    ]

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            pool = self._ISO299[:3]  # slot 8–12
        elif difficulty == "medium":
            pool = self._ISO299[:5]  # slot 8–18
        else:
            pool = self._ISO299  # all

        slot_opening, bolt_m, size = pool[int(rng.integers(0, len(pool)))]
        slot_opening = float(slot_opening)
        size = float(size)

        length = rng.uniform(size * 3, size * 10)
        slot_depth = round(size * rng.uniform(0.3, 0.5), 1)
        slot_back_w = round(size * rng.uniform(0.6, 0.85), 1)
        wall_t = round(size * rng.uniform(0.12, 0.22), 1)

        params = {
            "size": float(size),
            "mating_bolt": bolt_m,
            "length": round(length, 1),
            "slot_opening": slot_opening,
            "slot_depth": slot_depth,
            "slot_back_width": slot_back_w,
            "wall_thickness": wall_t,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            # end-face mounting holes
            params["end_hole_diameter"] = round(
                rng.uniform(3.0, min(6.0, size * 0.18)), 1
            )
            params["end_hole_inset"] = round(size / 2, 1)
            # 4-way slot (slots on all 4 faces)
            params["four_way"] = bool(rng.choice([True, False]))

        if difficulty == "hard":
            # Center bore: constrain so cbd/2 + slot_depth < size/2
            max_cbd = round((size / 2 - slot_depth) * 2 - 1, 1)
            if max_cbd >= 3:
                params["center_bore_diameter"] = round(
                    rng.uniform(3, max(3.5, min(max_cbd, size * 0.28))), 1
                )
            params["fillet_radius"] = round(rng.uniform(0.5, min(2.0, wall_t * 0.4)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        sz = params["size"]
        so = params["slot_opening"]
        sd = params["slot_depth"]
        sbw = params["slot_back_width"]
        wt = params["wall_thickness"]
        L = params["length"]

        if so >= sz * 0.7 or sd >= sz * 0.6 or sbw >= sz:
            return False
        if so >= sbw:
            return False
        if wt < 1.5 or wt >= sz * 0.25:
            return False
        if L < 20:
            return False
        # slot depth must not exceed half-size (slot can't go past center)
        if sd >= sz / 2 - 1:
            return False
        # back depth must be positive
        if sd <= (sbw - so) / 2 + 1:
            return False

        cbd = params.get("center_bore_diameter")
        if cbd:
            # bore must not intersect slot
            if cbd / 2 + sd >= sz / 2:
                return False

        # fillet must fit inside the T-slot geometry
        fr = params.get("fillet_radius")
        back_depth = sd - (sbw - so) / 2
        ledge_w = (sbw - so) / 2  # ledge width at neck-to-back transition
        if fr and (back_depth < fr * 2 or ledge_w < fr * 2):
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        sz = params["size"]
        L = params["length"]
        so = params["slot_opening"]  # opening width at face
        sd = params["slot_depth"]  # depth of slot
        sbw = params["slot_back_width"]  # back width of T
        wt = params["wall_thickness"]

        ops, tags = [], {
            "has_hole": False,
            "has_slot": True,
            "has_fillet": False,
            "has_chamfer": False,
            "symmetric_result": True,
        }

        hs = round(sz / 2, 3)  # half-size
        hso = round(so / 2, 3)  # half slot-opening
        hsbw = round(sbw / 2, 3)  # half slot-back-width

        # Build outer square profile with one T-slot on top face
        # Profile is on XY plane, extruded along Z
        # Outer square corners: (±hs, ±hs)
        # T-slot cuts into +Y face: opening at y=hs, depth=sd inward
        # Slot profile (from right side going CCW):
        pts = [
            (-hs, -hs),  # bottom-left
            (hs, -hs),  # bottom-right
            (hs, hs),  # top-right outer
            (hso, hs),  # right edge of slot opening
            (hso, hs - (sd - (sbw - so) / 2)),  # slot neck RHS
            (hsbw, hs - (sd - (sbw - so) / 2)),  # slot back RHS
            (hsbw, hs - sd),  # slot back top
            (-hsbw, hs - sd),  # slot back top left
            (-hsbw, hs - (sd - (sbw - so) / 2)),  # slot back LHS
            (-hso, hs - (sd - (sbw - so) / 2)),  # slot neck LHS
            (-hso, hs),  # left edge of slot opening
            (-hs, hs),  # top-left outer
        ]
        # Write as moveTo + series of lineTo + close
        ops.append(Op("moveTo", {"x": pts[0][0], "y": pts[0][1]}))
        for px, py in pts[1:]:
            ops.append(Op("lineTo", {"x": round(px, 4), "y": round(py, 4)}))
        ops.append(Op("close", {}))
        ops.append(Op("extrude", {"distance": L}))

        # 4-way slots on other faces (medium+)
        if params.get("four_way"):
            # Each slot: neck (narrow opening at face) + back (wide pocket inward)
            # neck_h = radial depth of neck; back_h = radial depth of back
            neck_h = round((sbw - so) / 2, 3)
            back_h = round(sd - neck_h, 3)

            # Bottom face (<Y): slot opens at y=-hs, goes +Y
            # On >Z plane: x=along-part-X (extent=sbw), y=along-part-Y (depth)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op("center", {"x": 0.0, "y": round(-hs + neck_h + back_h / 2, 3)})
            )
            ops.append(Op("rect", {"length": sbw, "width": back_h}))
            ops.append(Op("cutThruAll", {}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": 0.0, "y": round(-hs + neck_h / 2, 3)}))
            ops.append(Op("rect", {"length": so, "width": neck_h}))
            ops.append(Op("cutThruAll", {}))

            # Right face (>X): slot opens at x=hs, goes -X
            # On >Z plane: x=along-part-X (depth), y=along-part-Y (extent=sbw)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op("center", {"x": round(hs - neck_h - back_h / 2, 3), "y": 0.0})
            )
            ops.append(Op("rect", {"length": back_h, "width": sbw}))
            ops.append(Op("cutThruAll", {}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": round(hs - neck_h / 2, 3), "y": 0.0}))
            ops.append(Op("rect", {"length": neck_h, "width": so}))
            ops.append(Op("cutThruAll", {}))

            # Left face (<X): slot opens at x=-hs, goes +X (symmetric to right)
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(
                Op("center", {"x": round(-hs + neck_h + back_h / 2, 3), "y": 0.0})
            )
            ops.append(Op("rect", {"length": back_h, "width": sbw}))
            ops.append(Op("cutThruAll", {}))
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("center", {"x": round(-hs + neck_h / 2, 3), "y": 0.0}))
            ops.append(Op("rect", {"length": neck_h, "width": so}))
            ops.append(Op("cutThruAll", {}))

        # End mounting holes (medium+)
        ehd = params.get("end_hole_diameter")
        if ehd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("hole", {"diameter": ehd}))

        # Center bore (hard)
        cbd = params.get("center_bore_diameter")
        if cbd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": "<Z"}))
            ops.append(Op("hole", {"diameter": cbd}))

        # Fillet (hard, only when no four_way — four_way creates too many complex edges)
        fr = params.get("fillet_radius")
        if fr and not params.get("four_way"):
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": "|Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
