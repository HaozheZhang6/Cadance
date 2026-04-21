"""Capsule — cylinder with two hemispherical end caps.

Represents: pill/capsule container, pressure vessel, fluid reservoir.

Built from primitive union: cylinder (axis=Z) centered at origin + two spheres
at z=±h_cyl/2. Previous impl revolved a profile whose wire touched the axis of
revolution; the resulting pole singularity caused tessellation gaps at the
apices — rendered as a dark "rim" that made the solid pill look hollow.

Easy:   solid capsule body.
Medium: + equatorial weld ring (annular band at mid-height, union).
Hard:   + two end port stubs (short cylinders embedded into the hemispheres).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class CapsuleFamily(BaseFamily):
    name = "capsule"
    standard = "N/A"

    def sample_params(self, difficulty: str, rng) -> dict:
        r = round(rng.uniform(15, 60), 1)
        h_cyl = round(rng.uniform(20, 100), 1)

        params = {
            "radius": r,
            "cyl_height": h_cyl,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["ring_width"] = round(rng.uniform(3, max(3.5, min(r * 0.2, 10))), 1)
            params["ring_height"] = round(rng.uniform(4, max(4.5, min(r * 0.15, 8))), 1)

        if difficulty == "hard":
            params["stub_radius"] = round(
                rng.uniform(4, max(4.5, min(r * 0.35, 20))), 1
            )
            params["stub_height"] = round(rng.uniform(8, max(8.5, min(r * 0.6, 25))), 1)

        return params

    def validate_params(self, params: dict) -> bool:
        r = params["radius"]
        h_cyl = params["cyl_height"]

        if r < 10:
            return False
        if h_cyl < 15:
            return False

        rw = params.get("ring_width", 0)
        rh = params.get("ring_height", 0)
        if rw and rw >= r * 0.35:
            return False
        if rh and rh < 2:
            return False

        sr = params.get("stub_radius", 0)
        sh = params.get("stub_height", 0)
        if sr and sr >= r * 0.55:
            return False
        if sh and sh < 5:
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        r = round(params["radius"], 4)
        h_cyl = round(params["cyl_height"], 4)
        # All primitives along Z, body centered at origin:
        #   cylinder:  z ∈ [-h_cyl/2, h_cyl/2]
        #   top sphere centered at z=+h_cyl/2
        #   bottom sphere centered at z=-h_cyl/2
        # Total extent: z ∈ [-h_cyl/2 - r, h_cyl/2 + r]
        top_z = round(h_cyl / 2, 4)
        bot_z = round(-h_cyl / 2, 4)

        ops = []
        tags = {"has_hole": False, "has_fillet": False, "has_chamfer": False}

        ops.append(Op("cylinder", {"height": h_cyl, "radius": r}))
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0.0, 0.0, top_z], "rotate": [0, 0, 0]},
                        },
                        {"name": "sphere", "args": {"radius": r}},
                    ]
                },
            )
        )
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {"offset": [0.0, 0.0, bot_z], "rotate": [0, 0, 0]},
                        },
                        {"name": "sphere", "args": {"radius": r}},
                    ]
                },
            )
        )

        # Weld ring at equator (medium+): outer annular band, cylinder along Z
        # at z=0, radius=r+rw, height=rh. Union overlaps the body for radii ≤r
        # (no-op inside the body) and adds the r..r+rw annulus.
        rw = params.get("ring_width")
        rh = params.get("ring_height")
        if rw and rh:
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(rh, 4),
                                    "radius": round(r + rw, 4),
                                },
                            }
                        ]
                    },
                )
            )

        # End port stubs (hard): short cylinders at top and bottom poles,
        # embedded `overlap` mm into the hemispheres so the union has a
        # non-degenerate volumetric intersection (not just a tangent point).
        sr = params.get("stub_radius")
        sh = params.get("stub_height")
        if sr and sh:
            overlap = round(min(sr * 0.6, sh * 0.3, r * 0.5), 4)
            # Top stub: tip at z = top_z + r + sh - overlap, base at z = top_z + r - overlap
            #   → center at z = top_z + r - overlap + sh/2
            top_stub_z = round(top_z + r - overlap + sh / 2, 4)
            bot_stub_z = round(bot_z - r + overlap - sh / 2, 4)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, top_stub_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(sh, 4),
                                    "radius": round(sr, 4),
                                },
                            },
                        ]
                    },
                )
            )
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0.0, 0.0, bot_stub_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(sh, 4),
                                    "radius": round(sr, 4),
                                },
                            },
                        ]
                    },
                )
            )

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
