"""Battery holder — 3D-printed AA/AAA cell holder block.

Rectangular block with a row of cylindrical pockets sized to hold standard
round cells (AAA, AA, C, 18650 Li-ion). Slot openings on the sides let users
pop cells out and provide space for contact springs.

Keys: cell_type, cell_count, cell_d, cell_L, wall_t.

Easy:   2-cell AAA holder, pockets only.
Medium: 4-cell AA holder + finger slots on each pocket.
Hard:   4-cell 18650 holder + chamfered top rim + through-bores for contacts.

Reference: IEC 60086 cell dimensions (AAA=10.5 mm, AA=14.5 mm, 18650=18.4 mm).
"""

from ..pipeline.builder import Op, Program
from .base import BaseFamily

# IEC 60086 standard cells — (label, diameter_mm, length_mm)
_CELL_TYPES = {
    "AAA": (10.5, 44.5),
    "AA": (14.5, 50.5),
    "C": (26.2, 50.0),
    "18650": (18.4, 65.0),
    "21700": (21.0, 70.0),
}


class BatteryHolderFamily(BaseFamily):
    name = "battery_holder"
    standard = "IEC 60086"

    def sample_params(self, difficulty: str, rng) -> dict:
        if difficulty == "easy":
            cell_type = str(rng.choice(["AAA", "AA"]))
            n_cells = int(rng.choice([2, 3]))
        elif difficulty == "medium":
            cell_type = str(rng.choice(["AA", "AAA", "18650"]))
            n_cells = int(rng.choice([2, 3, 4]))
        else:
            cell_type = str(rng.choice(["18650", "21700", "C"]))
            n_cells = int(rng.choice([2, 3, 4]))

        cell_d, cell_L = _CELL_TYPES[cell_type]
        wall_t = 2.0
        pitch = round(cell_d + wall_t + 1.5, 1)

        block_L = round(pitch * n_cells + wall_t, 1)
        block_W = round(cell_d + 2 * wall_t, 1)
        block_T = round(cell_d * 0.65 + wall_t, 1)

        params = {
            "cell_type": cell_type,
            "cell_count": n_cells,
            "cell_d": float(cell_d),
            "cell_L": float(cell_L),
            "pitch": pitch,
            "block_L": block_L,
            "block_W": block_W,
            "block_T": block_T,
            "wall_t": wall_t,
            "difficulty": difficulty,
        }
        if difficulty in ("medium", "hard"):
            params["finger_slot_w"] = round(cell_d * 0.6, 1)
        if difficulty == "hard":
            params["rim_chamfer"] = 0.8
            params["contact_hole_d"] = round(cell_d * 0.25, 1)
        return params

    def validate_params(self, params: dict) -> bool:
        if params["cell_count"] < 1:
            return False
        if params["block_T"] <= params["cell_d"] * 0.4:
            return False
        if params["block_L"] <= params["pitch"] * params["cell_count"] * 0.9:
            return False
        return True

    def make_program(self, params: dict) -> Program:
        difficulty = params.get("difficulty", "easy")
        n = params["cell_count"]
        cell_d = params["cell_d"]
        cell_L = params["cell_L"]
        pitch = params["pitch"]
        L = params["block_L"]
        W = params["block_W"]
        T = params["block_T"]
        wall = params["wall_t"]

        tags = {
            "has_hole": True,
            "has_slot": False,
            "has_fillet": False,
            "has_chamfer": False,
            "rotational": False,
        }

        # Block layout: block extends along X (length = n_cells × pitch), cells
        # lie ALONG X too (cylinder axes parallel to X). The block is thus
        # long along X, narrow in Y, short in Z. Cell pocket: half-cylinder
        # cut from the top of the block.
        # Block dims: length = cell_L + 2*wall (along X), width W (along Y),
        # thickness T (along Z). Cells are positioned along Y.
        # Actually simpler: arrange cells along Y, pockets cut downward from top.
        # Block: length = L (Y direction), width = cell_L + 2*wall (X), height T
        block_x = round(cell_L + 2 * wall, 3)  # length along X
        block_y = round(pitch * n + wall, 3)  # length along Y
        block_z = T
        ops = [
            Op(
                "box",
                {"length": block_x, "width": block_y, "height": round(block_z, 3)},
            ),
        ]

        # Rim chamfer (hard)
        rc = params.get("rim_chamfer")
        if rc:
            tags["has_chamfer"] = True
            ops.append(Op("edges", {"selector": ">Z"}))
            ops.append(Op("chamfer", {"length": rc}))

        # Cell pockets: cylinders along X axis, cut from top half of block
        y_start = -((n - 1) / 2) * pitch
        cell_r = cell_d / 2
        pocket_cz = round(T / 2 - cell_r * 0.6 + 0.1, 4)  # so half-cylinder lips
        for i in range(n):
            cy = round(y_start + i * pitch, 4)
            ops.append(
                Op(
                    "cut",
                    {
                        "plane": "XY",
                        "ops": [
                            {
                                "name": "transformed",
                                "args": {
                                    "offset": [0, cy, pocket_cz],
                                    "rotate": [0, 90, 0],
                                },
                            },
                            {
                                "name": "cylinder",
                                "args": {
                                    "height": round(cell_L + 2, 3),
                                    "radius": round(cell_r, 3),
                                },
                            },
                        ],
                    },
                )
            )
            # Finger slot: short transverse slot on top of each pocket (medium+).
            # Axis along Y, bounded to one cell width — NOT spanning full block.
            fs_w = params.get("finger_slot_w")
            if fs_w:
                slot_len = round(cell_d * 0.8, 3)
                ops.append(
                    Op(
                        "cut",
                        {
                            "plane": "XY",
                            "ops": [
                                {
                                    "name": "transformed",
                                    "args": {
                                        "offset": [0, cy, pocket_cz],
                                        "rotate": [90, 0, 0],
                                    },
                                },
                                {
                                    "name": "cylinder",
                                    "args": {
                                        "height": slot_len,
                                        "radius": round(fs_w / 2, 3),
                                    },
                                },
                            ],
                        },
                    )
                )
            # Contact through-holes at cell ends (hard)
            chd = params.get("contact_hole_d")
            if chd:
                for sign in (-1, 1):
                    cx = round(sign * (cell_L / 2 + wall / 2), 4)
                    ops.append(
                        Op(
                            "cut",
                            {
                                "plane": "XY",
                                "ops": [
                                    {
                                        "name": "transformed",
                                        "args": {
                                            "offset": [cx, cy, pocket_cz],
                                            "rotate": [0, 90, 0],
                                        },
                                    },
                                    {
                                        "name": "cylinder",
                                        "args": {
                                            "height": round(wall * 2 + 1, 3),
                                            "radius": round(chd / 2, 3),
                                        },
                                    },
                                ],
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
