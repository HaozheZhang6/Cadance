"""Threaded adapter / hex fitting — hex prism + stepped cylinder union.

ASME B1.20.1 NPT (National Pipe Taper) fittings.
Table: (nps_label, stub_od_mm, hex_af_mm, engagement_mm)
Hex AF and engagement lengths per ASME B1.20.1 Table 3 + fitting catalogue.

Easy:   hex prism + one cylindrical stub (small NPS)
Medium: + through bore + chamfer on hex
Hard:   + second stepped stub on other end (reducer adapter, different NPS)

Reference: ASME B1.20.1-2013 — Pipe threads, general purpose (NPT); Table 3 (L1 engagement per NPS)
"""

import math

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# ASME B1.20.1 NPT — (nps_label, stub_od_mm, hex_af_mm, engagement_mm)
# hex_af: standard wrench flat size for hex coupling body
# engagement_mm: ASME B1.20.1 Table 3 hand-tight engagement length L1
_ASME_B1201_NPT = [
    ("NPS 1/8", 10.3, 14, 4.0),
    ("NPS 1/4", 13.7, 17, 5.8),
    ("NPS 3/8", 17.1, 19, 6.4),
    ("NPS 1/2", 21.3, 24, 8.1),
    ("NPS 3/4", 26.7, 30, 9.5),
    ("NPS 1", 33.4, 38, 10.4),
    ("NPS 1-1/4", 42.2, 46, 12.7),
    ("NPS 1-1/2", 48.3, 52, 12.7),
    ("NPS 2", 60.3, 65, 15.5),
]

_SMALL = _ASME_B1201_NPT[:4]  # NPS 1/8 – 1/2
_MID = _ASME_B1201_NPT[1:7]  # NPS 1/4 – 1-1/4
_ALL = _ASME_B1201_NPT  # NPS 1/8 – 2


class ThreadedAdapterFamily(BaseFamily):
    name = "threaded_adapter"
    standard = "ASME B1.20.1"

    def sample_params(self, difficulty: str, rng) -> dict:
        # hard requires a smaller nps2 — exclude the smallest two entries
        hard_pool = _ASME_B1201_NPT[2:]  # NPS 3/8 and up (always have a smaller nps2)
        pool = (
            _SMALL
            if difficulty == "easy"
            else (_MID if difficulty == "medium" else hard_pool)
        )
        nps, stub_od, af, eng = pool[int(rng.integers(0, len(pool)))]

        stub_r = round(stub_od / 2, 2)
        # hex height: 0.35–0.50 × AF (standard body thickness for hex couplings)
        hex_h = round(float(af) * float(rng.choice([0.35, 0.40, 0.45, 0.50])), 1)
        # stub length: 2–4× NPT engagement length (thread nipple engagement)
        stub_h = round(eng * float(rng.choice([2.0, 2.5, 3.0, 3.5, 4.0])), 1)
        # shoulder: small transition taper between hex and stub
        shoulder_h = round(eng * 0.5, 1)
        shoulder_r = round(stub_r * 1.10, 1)
        # bore: ~65% of stub OD (typical wall ratio for NPT fittings)
        bore_r = round(stub_r * 0.65, 1)

        params = {
            "nps": nps,
            "hex_af": float(af),
            "hex_height": hex_h,
            "stub_radius": stub_r,
            "stub_height": stub_h,
            "shoulder_height": shoulder_h,
            "shoulder_radius": shoulder_r,
            "bore_radius": bore_r,
            "difficulty": difficulty,
        }

        if difficulty in ("medium", "hard"):
            params["chamfer_length"] = round(hex_h * 0.07, 1)

        if difficulty == "hard":
            # Reducer: second end is a smaller NPS
            smaller_pool = [r for r in _ASME_B1201_NPT if r[2] < af]
            if smaller_pool:
                nps2, stub_od2, af2, eng2 = smaller_pool[
                    int(rng.integers(0, len(smaller_pool)))
                ]
                stub2_r = round(stub_od2 / 2, 2)
                stub2_h = round(eng2 * float(rng.choice([2.0, 2.5, 3.0])), 1)
                shoulder2_h = round(eng2 * 0.5, 1)
                shoulder2_r = round(stub2_r * 1.10, 1)
                params["nps2"] = nps2
                params["stub2_radius"] = stub2_r
                params["stub2_height"] = stub2_h
                params["shoulder2_height"] = shoulder2_h
                params["shoulder2_radius"] = shoulder2_r
                # Knurled grip ring
                knurl_r = round(stub2_r * 1.15, 2)
                knurl_h = round(hex_h * 0.35, 1)
                params["knurl_radius"] = knurl_r
                params["knurl_height"] = knurl_h
                params["n_knurl_slots"] = int(rng.choice([12, 16, 20]))

        return params

    def validate_params(self, params: dict) -> bool:
        haf = params["hex_af"]
        sr = params["stub_radius"]
        hex_r = haf / 2 / math.cos(math.radians(30))

        if sr >= hex_r * 0.95:
            return False
        if sr < 3:
            return False

        br = params.get("bore_radius")
        if br and br >= sr * 0.85:
            return False

        shr = params.get("shoulder_radius")
        if shr and shr >= hex_r:
            return False

        s2r = params.get("stub2_radius")
        if s2r and s2r >= sr:
            return False

        kr = params.get("knurl_radius")
        if kr and s2r and (kr <= s2r or kr >= hex_r):
            return False

        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        haf = params["hex_af"]
        hh = params["hex_height"]
        sr = params["stub_radius"]
        sh = params["stub_height"]

        hex_diam = round(haf / math.cos(math.radians(30)), 3)

        ops, tags = [], {
            "has_hole": False,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
        }

        ops.append(Op("polygon", {"n": 6, "diameter": hex_diam}))
        ops.append(Op("extrude", {"distance": hh}))

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

        cl = params.get("chamfer_length")
        if cl:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": cl}))
            ops.append(Op("faces", {"selector": "<Z"}))
            ops.append(Op("chamfer", {"length": cl}))

        s2r = params.get("stub2_radius")
        s2h = params.get("stub2_height")
        sh2r = params.get("shoulder2_radius")
        sh2h = params.get("shoulder2_height")
        if s2r and s2h and sh2r and sh2h:
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

        kr = params.get("knurl_radius")
        kh = params.get("knurl_height")
        nks = params.get("n_knurl_slots")
        if kr and kh and nks and sh2h:
            knurl_z = round(-sh2h - kh / 2, 3)
            slot_w = round(2 * math.pi * kr / nks * 0.35, 3)
            slot_d = round(kr - (s2r or sr), 3)
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
