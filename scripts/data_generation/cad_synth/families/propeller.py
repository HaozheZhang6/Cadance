"""Propeller / fan blade — hub with N pitched flat blades.

Structural type: hub cylinder + N box blades, each twisted/pitched.
Distinct from impeller: open blades, explicit pitch angle, taper toward tip.

variant=2blade:  2-blade propeller
variant=3blade:  3-blade propeller
variant=4blade:  4-blade propeller

Easy:   hub + N flat tapered blades
Medium: + narrower tip chord + bore
Hard:   lofted ellipse airfoil blade (root→tip taper + twist) + bore + fillet
"""

import math
from .base import BaseFamily
from ..pipeline.builder import Op, Program

VARIANTS = ["2blade", "3blade", "4blade"]


class PropellerFamily(BaseFamily):
    name = "propeller"

    def sample_params(self, difficulty: str, rng) -> dict:
        variant = rng.choice(VARIANTS)
        n_blades = int(variant[0])
        hub_r = rng.uniform(8, 25)
        hub_h = rng.uniform(hub_r * 0.6, hub_r * 1.5)
        blade_len = rng.uniform(hub_r * 2.2, hub_r * 4.2)
        root_chord = rng.uniform(hub_r * 0.9, hub_r * 1.8)
        root_thickness = rng.uniform(max(2.0, root_chord * 0.18), max(root_chord * 0.22, root_chord * 0.32))
        pitch_deg = rng.uniform(10, 40)   # blade pitch angle from hub plane

        params = {
            "variant": variant,
            "n_blades": n_blades,
            "hub_radius": round(hub_r, 1),
            "hub_height": round(hub_h, 1),
            "blade_length": round(blade_len, 1),
            "root_chord": round(root_chord, 1),
            "root_thickness": round(root_thickness, 2),
            "pitch_angle": round(pitch_deg, 1),
            "difficulty": difficulty,
        }

        spinner_height = round(rng.uniform(hub_r * 0.3, hub_r * 0.55), 1)
        params["spinner_height"] = spinner_height

        if difficulty in ("medium", "hard"):
            tip_chord = round(root_chord * rng.uniform(0.45, 0.7), 1)
            params["tip_chord"] = tip_chord
            params["bore_diameter"] = round(hub_r * rng.uniform(0.3, 0.6), 1)

        if difficulty == "hard":
            tip_pitch = round(pitch_deg * rng.uniform(0.4, 0.8), 1)
            tip_thickness = round(root_thickness * rng.uniform(0.35, 0.55), 2)
            params["tip_pitch_angle"] = tip_pitch
            params["tip_thickness"] = tip_thickness
            params["fillet_radius"] = round(rng.uniform(1, max(1.1, hub_r * 0.12)), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        hr = params["hub_radius"]
        bl = params["blade_length"]
        rc = params["root_chord"]
        rt = params["root_thickness"]

        if bl < hr * 2 or rt < 2.0:
            return False
        if params["pitch_angle"] < 5 or params["pitch_angle"] > 50:
            return False

        tc = params.get("tip_chord")
        if tc and tc >= rc:
            return False

        bd = params.get("bore_diameter")
        if bd and bd >= hr * 0.8:
            return False

        tp = params.get("tip_pitch_angle")
        if tp and tp >= params["pitch_angle"]:
            return False

        tt = params.get("tip_thickness")
        if tt and tt >= rt:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        variant = params.get("variant", "3blade")
        n_blades = params["n_blades"]
        hub_r = params["hub_radius"]
        hub_h = params["hub_height"]
        blade_len = params["blade_length"]
        root_chord = params["root_chord"]
        root_t = params["root_thickness"]
        pitch = params["pitch_angle"]
        tip_chord = params.get("tip_chord", root_chord * 0.65)
        tip_pitch = params.get("tip_pitch_angle", pitch * 0.75)

        ops, tags = [], {
            "has_hole": False, "has_slot": False,
            "has_fillet": False, "has_chamfer": False,
            "rotational": True,
        }

        # Hub cylinder
        ops.append(Op("cylinder", {"height": hub_h, "radius": hub_r}))

        # Spinner (nose cone) — loft from hub face to point
        spinner_h = params.get("spinner_height", round(hub_r * 0.4, 1))
        ops.append(Op("workplane", {"selector": ">Z"}))
        ops.append(Op("circle", {"radius": round(hub_r * 0.9, 3)}))
        ops.append(Op("workplane_offset", {"offset": spinner_h}))
        ops.append(Op("circle", {"radius": 1.5}))
        ops.append(Op("loft", {"combine": True}))

        # Bore (medium+)
        bd = params.get("bore_diameter")
        if bd:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": bd}))

        root_inset = round(hub_r * 0.3, 3)

        if difficulty == "hard":
            # Lofted airfoil blade: ellipse cross-sections lofted along span.
            # Transform sequence: azimuthal rotate → Ry(90°) to align local-Z radially
            # outward (span direction) → root-pitch twist → ellipse → workplane_offset →
            # differential tip twist → tip ellipse → loft.
            tip_t = params.get("tip_thickness", round(root_t * 0.45, 2))
            twist_deg = round(tip_pitch - pitch, 3)  # differential root→tip untwist

            for i in range(n_blades):
                blade_angle = round(360.0 * i / n_blades, 3)
                ops.append(Op("union", {"ops": [
                    # Step 1: move to hub equator (z=0), rotate to blade azimuth
                    {"name": "transformed", "args": {
                        "offset": [0, 0, 0],
                        "rotate": [0, 0, blade_angle],
                    }},
                    # Step 2: Ry(90°) makes local-Z = radially outward (span axis);
                    # offset [0,0, hub_r-root_inset] moves root to hub surface
                    {"name": "transformed", "args": {
                        "offset": [0, 0, round(hub_r - root_inset, 3)],
                        "rotate": [0, 90, 0],
                    }},
                    # Step 3: pitch rotation of cross-section around chord (Y) axis
                    {"name": "transformed", "args": {
                        "offset": [0, 0, 0],
                        "rotate": [0, round(pitch, 3), 0],
                    }},
                    # Root cross-section: ellipse(thickness/2, chord/2)
                    {"name": "ellipse", "args": {
                        "xRadius": round(root_t / 2, 3),
                        "yRadius": round(root_chord / 2, 3),
                    }},
                    # Span offset to tip
                    {"name": "workplane_offset", "args": {"offset": round(blade_len, 3)}},
                    # Differential tip untwist around chord (Y) axis
                    {"name": "transformed", "args": {
                        "offset": [0, 0, 0],
                        "rotate": [0, round(twist_deg, 3), 0],
                    }},
                    # Tip cross-section: smaller and thinner
                    {"name": "ellipse", "args": {
                        "xRadius": round(tip_t / 2, 3),
                        "yRadius": round(tip_chord / 2, 3),
                    }},
                    {"name": "loft", "args": {"combine": True}},
                ]}))
        else:
            # Flat swept-planform blade (easy / medium) — 5-point profile per reference:
            # (0, ±root_chord/2) → (len*0.72, ±tip_chord*0.55) → (len, 0.0)
            blade_z = round((hub_h - root_t) / 2, 3)
            for i in range(n_blades):
                blade_angle = round(360.0 * i / n_blades, 3)
                bl  = round(blade_len, 3)
                rc2 = round(root_chord / 2, 3)
                tc  = tip_chord if difficulty == "medium" else round(root_chord * 0.65, 3)
                blade_pts = [
                    [0.0,              round(-rc2, 3)],
                    [0.0,              rc2],
                    [round(bl * 0.72, 3), round(tc * 0.55, 3)],
                    [bl,               0.0],
                    [round(bl * 0.72, 3), round(-tc * 0.55, 3)],
                ]
                ops.append(Op("union", {"ops": [
                    {"name": "transformed", "args": {
                        "offset": [0, 0, blade_z],
                        "rotate": [0, 0, blade_angle],
                    }},
                    {"name": "transformed", "args": {
                        "offset": [root_inset, 0, 0],
                        "rotate": [round(pitch, 3), 0, 0],
                    }},
                    {"name": "polyline", "args": {"points": blade_pts}},
                    {"name": "close", "args": {}},
                    {"name": "extrude", "args": {"distance": round(root_t, 3)}},
                ]}))

        # Fillet on hub-blade junctions (medium flat blades only; lofted blades skip)
        fr = params.get("fillet_radius")
        if fr and difficulty != "hard":
            tags["has_fillet"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("fillet", {"radius": fr}))

        return Program(family=self.name, difficulty=difficulty,
                       params=params, ops=ops, feature_tags=tags)
