"""Centrifugal impeller — back plate + hub + N swept blades + front retaining ring.

Structure (always present, all difficulties):
  back_plate  : flat disc (full outer radius, at z=0)
  hub         : centre cylinder on back plate (for shaft)
  N blades    : swept parallelogram polygon, extruded, rotated around Z
  front_ring  : annular retaining ring at blade tip face

Difficulty controls blade geometry:
  easy   : straight radial blades (sweep_deg ≈ 0), fewer blades, bore
  medium : backward-swept blades (-15° to -35°), more blades, bore
  hard   : deeper sweep, center recess pocket on top face
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program


class ImpellerFamily(BaseFamily):
    name = "impeller"

    def sample_params(self, difficulty: str, rng) -> dict:
        outer_r        = round(rng.uniform(25, 65), 1)   # outer (rim) radius [mm]
        hub_r          = round(rng.uniform(outer_r * 0.15, outer_r * 0.30), 1)
        hub_h          = round(rng.uniform(outer_r * 0.35, outer_r * 0.65), 1)
        back_t         = round(rng.uniform(outer_r * 0.05, outer_r * 0.12), 1)
        blade_h        = round(rng.uniform(outer_r * 0.25, outer_r * 0.55), 1)
        blade_t        = round(rng.uniform(outer_r * 0.04, outer_r * 0.10), 1)
        blade_span     = round(rng.uniform(outer_r * 0.45, outer_r * 0.75), 1)
        n_blades       = int(rng.choice([6, 7, 8, 10] if difficulty != "easy" else [5, 6, 7]))
        bore_d         = round(rng.uniform(hub_r * 0.5, max(hub_r * 0.51, hub_r * 0.85)), 1)
        front_ring_t   = round(rng.uniform(outer_r * 0.03, outer_r * 0.07), 1)
        # ring inner radius must be INSIDE blade outer extent so blades connect to ring
        blade_outer    = hub_r + blade_span * 0.9
        front_ring_ir  = round(blade_outer - rng.uniform(1.0, max(1.1, outer_r * 0.05)), 1)

        # backward sweep angle [degrees]: 0=radial, negative=backward sweep
        if difficulty == "easy":
            sweep_deg = round(rng.uniform(-8, 5), 1)
        elif difficulty == "medium":
            sweep_deg = round(rng.uniform(-30, -10), 1)
        else:
            sweep_deg = round(rng.uniform(-40, -15), 1)

        params = {
            "outer_radius":      outer_r,
            "hub_radius":        hub_r,
            "hub_height":        hub_h,
            "back_plate_thickness": back_t,
            "blade_height":      blade_h,
            "blade_thickness":   blade_t,
            "blade_span":        blade_span,
            "n_blades":          n_blades,
            "sweep_angle":       sweep_deg,
            "bore_diameter":     bore_d,
            "front_ring_thickness": front_ring_t,
            "front_ring_inner_radius": front_ring_ir,
            "difficulty":        difficulty,
        }

        # Center recess pocket (hard) — small annular groove inside the hub boss
        if difficulty == "hard":
            recess_r = round(hub_r * rng.uniform(1.2, 1.7), 1)
            recess_d = round(rng.uniform(1.5, max(1.6, blade_t * 0.8)), 1)
            params.update(center_recess_radius=recess_r, center_recess_depth=recess_d)

        return params

    def validate_params(self, params: dict) -> bool:
        or_  = params["outer_radius"]
        hr   = params["hub_radius"]
        bh   = params["blade_height"]
        bt   = params["blade_thickness"]
        bs   = params["blade_span"]
        bd   = params["bore_diameter"]
        n    = params["n_blades"]
        frir = params["front_ring_inner_radius"]

        if hr >= or_ * 0.4 or bd >= hr * 0.9:
            return False
        if bh < 5 or bt < 1.0:
            return False
        # blade span must fit inside rim (hub surface + span < outer_r)
        if hr + bs > or_ * 1.05:
            return False
        # blades must not overlap at hub circle
        arc_gap = 2 * math.pi * hr / n - bt
        if arc_gap < 1.5:
            return False
        # front ring inner must be clearly inside outer
        if frir >= or_ * 0.97 or frir <= hr * 1.2:
            return False

        cr = params.get("center_recess_radius")
        if cr and cr >= or_ * 0.5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty  = params.get("difficulty", "easy")
        or_         = params["outer_radius"]
        hub_r       = params["hub_radius"]
        hub_h       = params["hub_height"]
        back_t      = params["back_plate_thickness"]
        blade_h     = params["blade_height"]
        blade_t     = params["blade_thickness"]
        blade_span  = params["blade_span"]
        n           = params["n_blades"]
        sweep       = params["sweep_angle"]
        bore_d      = params["bore_diameter"]
        ring_t      = params["front_ring_thickness"]
        ring_ir     = params["front_ring_inner_radius"]

        ops, tags = [], {
            "has_hole": True, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": True, "pattern_like": True,
        }

        # -------------------------------------------------------
        # 1. Back plate — full disc (z = -back_t/2 .. +back_t/2, centered at z=0)
        # -------------------------------------------------------
        ops.append(Op("cylinder", {"height": round(back_t, 3), "radius": round(or_, 3)}))

        # -------------------------------------------------------
        # 2. Hub — cylinder on top of back plate (0.5mm overlap to avoid co-planar)
        # -------------------------------------------------------
        ops.append(Op("union", {"ops": [
            {"name": "transformed", "args": {
                "offset": [0, 0, round(back_t / 2 + hub_h / 2 - 0.5, 3)],
                "rotate": [0, 0, 0],
            }},
            {"name": "cylinder", "args": {"height": round(hub_h, 3), "radius": round(hub_r, 3)}},
        ]}))

        # -------------------------------------------------------
        # 3. N swept blades
        #    Blade profile (local XY, centred at local origin):
        #      inner edge at x ≈ -blade_span*0.42 (points toward hub)
        #      outer edge at x ≈ +blade_span*0.48 (points toward rim)
        #    Placement: two transforms in sequence:
        #      (a) rotate to azimuth i*360/n around Z
        #      (b) move to (hub_r + blade_span*0.42, 0, z_blade) and apply sweep
        # -------------------------------------------------------
        blade_pts = [
            (round(-blade_span * 0.42, 3), round(-blade_t * 0.60, 3)),
            (round(-blade_span * 0.18, 3), round( blade_t * 0.55, 3)),
            (round( blade_span * 0.48, 3), round( blade_t * 0.42, 3)),
            (round( blade_span * 0.24, 3), round(-blade_t * 0.75, 3)),
        ]
        # blade base z: 0.5mm inside back_plate for volumetric overlap
        blade_z = round(back_t / 2 - 0.5, 3)
        # radial offset: local origin sits at hub_r + blade_span*0.42; -0.5 overlap with hub
        cx = round(hub_r + blade_span * 0.42 - 0.5, 3)

        for i in range(n):
            azimuth = round(360.0 * i / n, 3)    # blade rotation around Z axis
            ops.append(Op("union", {"ops": [
                # Step 1: rotate workplane to blade's azimuthal position
                {"name": "transformed", "args": {
                    "offset": [0, 0, 0],
                    "rotate": [0, 0, azimuth],
                }},
                # Step 2: move to blade centre radially + apply backward sweep in local frame
                {"name": "transformed", "args": {
                    "offset": [cx, 0, blade_z],
                    "rotate": [0, 0, round(sweep, 3)],
                }},
                {"name": "polyline", "args": {"points": blade_pts}},
                {"name": "close", "args": {}},
                {"name": "extrude", "args": {"distance": round(blade_h, 3)}},
            ]}))

        # -------------------------------------------------------
        # 4. Front retaining ring — ANNULAR disc (ring_ir to or_) at blade tip z.
        #    Two-circle extrude creates the annulus; inner opening allows axial flow.
        #    Z overlap with blade tips ensures volumetric connectivity.
        # -------------------------------------------------------
        z_overlap = round(min(2.0, ring_t * 0.4), 3)
        ring_z = round(blade_z + blade_h + ring_t / 2 - z_overlap, 3)
        ring_bottom = round(ring_z - ring_t / 2, 3)
        ops.append(Op("union", {"ops": [
            {"name": "transformed", "args": {
                "offset": [0, 0, ring_bottom],
                "rotate": [0, 0, 0],
            }},
            {"name": "circle", "args": {"radius": round(or_, 3)}},
            {"name": "circle", "args": {"radius": round(ring_ir, 3)}},
            {"name": "extrude", "args": {"distance": round(ring_t, 3)}},
        ]}))

        # -------------------------------------------------------
        # 5. Central bore (all difficulties)
        # -------------------------------------------------------
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("hole", {"diameter": round(bore_d, 3)}))

        # -------------------------------------------------------
        # 6. Center recess pocket (hard) — annular groove at top face
        # -------------------------------------------------------
        cr = params.get("center_recess_radius")
        cd = params.get("center_recess_depth")
        if cr and cd:
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("circle", {"radius": round(cr, 3)}))
            ops.append(Op("cutBlind", {"depth": round(cd, 3)}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
