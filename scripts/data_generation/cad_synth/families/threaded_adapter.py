"""Threaded adapter / hex fitting — hex prism + stepped cylinder union.

Structural type: multi-body union (hex body + cylindrical nipples).
Covers: pipe adapters, NPT fittings, hydraulic connectors, hex couplings.

Easy:   hex prism + one cylindrical stub
Medium: + through bore + chamfer on hex
Hard:   + second stepped stub on other end + knurled ring (approximated)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily


class ThreadedAdapterFamily(BaseFamily):
    name = "threaded_adapter"
    standard = "ASME B1.20.1"

    def sample_params(self, difficulty: str, rng) -> dict:
        hex_across_flats = rng.uniform(14, 50)  # hex wrench size (AF)
        hex_h = rng.uniform(8, max(8.1, hex_across_flats * 0.6))
        stub_r = round(hex_across_flats * rng.uniform(0.28, 0.42), 1)
        stub_h = rng.uniform(10, max(10.1, hex_across_flats * 1.2))

        shoulder_h = round(rng.uniform(3, max(3.1, hex_h * 0.3)), 1)
        shoulder_r = round(stub_r * rng.uniform(1.08, 1.20), 1)

        params = {
            "hex_af": round(hex_across_flats, 1),
            "hex_height": round(hex_h, 1),
            "stub_radius": round(stub_r, 1),
            "stub_height": round(stub_h, 1),
            "shoulder_height": shoulder_h,
            "shoulder_radius": shoulder_r,
            "difficulty": difficulty,
        }

        bore_r = round(stub_r * rng.uniform(0.45, 0.70), 1)
        params["bore_radius"] = bore_r

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(
                rng.uniform(0.5, max(0.6, hex_h * 0.08)), 1
            )

        if difficulty == "hard":
            # Second stub on the other end (different size)
            stub2_r = round(stub_r * rng.uniform(0.6, max(0.61, 0.95)), 1)
            stub2_h = round(rng.uniform(8, max(8.1, hex_across_flats * 0.9)), 1)
            shoulder2_h = round(rng.uniform(3, max(3.1, hex_h * 0.3)), 1)
            shoulder2_r = round(stub2_r * rng.uniform(1.08, 1.20), 1)
            params["stub2_radius"] = stub2_r
            params["stub2_height"] = stub2_h
            params["shoulder2_height"] = shoulder2_h
            params["shoulder2_radius"] = shoulder2_r
            # Knurled ring: between hex bottom and stub2
            knurl_r = round(stub2_r * rng.uniform(1.05, 1.20), 2)
            knurl_h = round(rng.uniform(4, max(4.1, hex_h * 0.4)), 1)
            n_knurl = int(rng.choice([12, 16, 20]))
            params["knurl_radius"] = knurl_r
            params["knurl_height"] = knurl_h
            params["n_knurl_slots"] = n_knurl

        return params

    def validate_params(self, params: dict) -> bool:
        haf = params["hex_af"]
        sr = params["stub_radius"]
        # hex circumscribed radius = af / cos(30°)
        hex_r = haf / 2 / math.cos(math.radians(30))
        if sr >= hex_r * 0.95:
            return False
        if sr < 3:
            return False

        br = params.get("bore_radius")
        if br and br >= sr * 0.8:
            return False

        s2r = params.get("stub2_radius")
        if s2r and s2r >= sr:
            return False

        shr = params.get("shoulder_radius")
        if shr and shr >= hex_r:
            return False

        kr = params.get("knurl_radius")
        s2r = params.get("stub2_radius")
        if kr and s2r and (kr <= s2r or kr >= hex_r):
            return False
        elif kr and not s2r and (kr <= sr or kr >= hex_r):
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        haf = params["hex_af"]
        hh = params["hex_height"]
        sr = params["stub_radius"]
        sh = params["stub_height"]

        # hex circumscribed diameter
        hex_diam = round(haf / math.cos(math.radians(30)), 3)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        # Hex body (6-sided polygon extruded)
        ops.append(Op("polygon", {"n": 6, "diameter": hex_diam}))
        ops.append(Op("extrude", {"distance": hh}))

        # Shoulder transition (hex → stub)
        shr = params["shoulder_height"]
        srr = params["shoulder_radius"]
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, round(hh + shr / 2, 3)],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "cylinder", "args": {"height": shr, "radius": srr}},
                    ]
                },
            )
        )

        # Stub cylinder on top
        ops.append(
            Op(
                "union",
                {
                    "ops": [
                        {
                            "name": "transformed",
                            "args": {
                                "offset": [0, 0, round(hh + shr + sh / 2, 3)],
                                "rotate": [0, 0, 0],
                            },
                        },
                        {"name": "cylinder", "args": {"height": sh, "radius": sr}},
                    ]
                },
            )
        )

        # Chamfer hex top/bottom edges (medium+)
        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        # Second stub on bottom (hard)
        s2r = params.get("stub2_radius")
        s2h = params.get("stub2_height")
        sh2r = params.get("shoulder2_radius")
        sh2h = params.get("shoulder2_height")
        if s2r and s2h and sh2r and sh2h:
            # Shoulder2 (hex bottom → stub2)
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(-sh2h / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": sh2h, "radius": sh2r},
                            },
                        ]
                    },
                )
            )
            # Stub2
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, round(-sh2h - s2h / 2, 3)],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {"height": s2h, "radius": s2r},
                            },
                        ]
                    },
                )
            )

        # Knurled ring — thin cylinder with polar slots (hard), between hex and stub2
        kr = params.get("knurl_radius")
        kh = params.get("knurl_height")
        nks = params.get("n_knurl_slots")
        if kr and kh and nks and sh2h:
            knurl_z = round(-sh2h - kh / 2, 3)
            slot_w = round(2 * math.pi * kr / nks * 0.35, 3)
            slot_d = round(kr - (s2r or sr), 3)
            # Add knurl body
            ops.append(
                Op(
                    "union",
                    {
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, 0, knurl_z],
                                    "rotate": [0, 0, 0],
                                },
                            },
                            {"name": "cylinder", "args": {"height": kh, "radius": kr}},
                        ]
                    },
                )
            )
            # Slot cuts around knurl
            for i in range(nks):
                angle_deg = round(360.0 * i / nks, 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [kr, 0, knurl_z],
                                        "rotate": [0, 0, angle_deg],
                                    },
                                },
                                {
                                    "name": "box",
                                    "args": {
                                        "length": slot_d * 2,
                                        "width": slot_w,
                                        "height": kh * 1.2,
                                        "centered": True,
                                    },
                                },
                            ]
                        },
                    )
                )

        # Through bore — always present, cut after all unions so stub2 is also hollow
        br = params.get("bore_radius")
        if br:
            tags["has_hole"] = True
            ops.append(Op("workplane", {"selector": ">Z"}))
            ops.append(Op("hole", {"diameter": br * 2}))

        return Program(
            family=self.name,
            difficulty=difficulty,
            params=params,
            ops=ops,
            feature_tags=tags,
        )
