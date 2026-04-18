#!/usr/bin/env python
"""Generate STEP files for evaluation using OCP (platform-compatible)."""

import json
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Pnt
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer


def export_step(shape, output_path: Path) -> bool:
    """Export shape to STEP file."""
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(str(output_path))
    return status == 1


def generate_simple_box(output_dir: Path):
    """L1_01: Simple box - 10x20x5mm."""
    box = BRepPrimAPI_MakeBox(10.0, 20.0, 5.0).Shape()

    path = output_dir / "L1_01_simple_box.step"
    export_step(box, path)

    return {
        "name": "simple_box",
        "level": 1,
        "description": "Basic rectangular box",
        "expected": {"volume": 1000.0, "bbox": [10.0, 20.0, 5.0]},
        "path": str(path),
    }


def generate_cylinder(output_dir: Path):
    """L1_02: Simple cylinder - radius 5mm, height 10mm."""
    cyl = BRepPrimAPI_MakeCylinder(5.0, 10.0).Shape()

    path = output_dir / "L1_02_cylinder.step"
    export_step(cyl, path)

    return {
        "name": "cylinder",
        "level": 1,
        "description": "Basic cylinder",
        "expected": {"volume": 785.4, "bbox": [10.0, 10.0, 10.0]},  # π * 5^2 * 10
        "path": str(path),
    }


def generate_l_bracket(output_dir: Path):
    """L2: L-bracket - base + vertical wall."""
    # Base: 50x60x5mm
    base = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 50.0, 60.0, 5.0).Shape()

    # Wall: 50x4x30mm at back
    wall = BRepPrimAPI_MakeBox(gp_Pnt(0, 56, 5), 50.0, 4.0, 30.0).Shape()

    # Fuse
    fuse_op = BRepAlgoAPI_Fuse(base, wall)
    fuse_op.Build()
    bracket = fuse_op.Shape()

    path = output_dir / "L2_l_bracket.step"
    export_step(bracket, path)

    return {
        "name": "l_bracket",
        "level": 2,
        "description": "L-shaped bracket with wall",
        "expected": {
            "volume": 21000.0,  # 50*60*5 + 50*4*30
            "bbox": [50.0, 60.0, 35.0],
        },
        "path": str(path),
    }


def generate_thin_wall_warning(output_dir: Path):
    """L3: Thin wall part (should trigger DFM warning)."""
    # Box with 1mm wall thickness (below typical 2mm threshold)
    thin_box = BRepPrimAPI_MakeBox(50.0, 50.0, 1.0).Shape()

    path = output_dir / "L3_thin_wall.step"
    export_step(thin_box, path)

    return {
        "name": "thin_wall",
        "level": 3,
        "description": "Part with thin wall (DFM risk)",
        "expected": {
            "volume": 2500.0,
            "bbox": [50.0, 50.0, 1.0],
            "warnings": ["thin_wall"],
        },
        "path": str(path),
    }


def generate_degenerate_geometry(output_dir: Path):
    """L4: Degenerate geometry (should fail verification)."""
    # Zero-height box (degenerate)
    degenerate = BRepPrimAPI_MakeBox(10.0, 10.0, 0.0001).Shape()

    path = output_dir / "L4_degenerate.step"
    export_step(degenerate, path)

    return {
        "name": "degenerate",
        "level": 4,
        "description": "Degenerate geometry (should fail)",
        "expected": {"volume": 0.0, "errors": ["degenerate_geometry"]},
        "path": str(path),
    }


def main():
    """Generate all test STEP files."""
    output_dir = Path(__file__).parent.parent / "tests" / "evaluation_steps"
    output_dir.mkdir(parents=True, exist_ok=True)

    generators = [
        generate_simple_box,
        generate_cylinder,
        generate_l_bracket,
        generate_thin_wall_warning,
        generate_degenerate_geometry,
    ]

    test_cases = []
    for gen in generators:
        print(f"Generating {gen.__name__}...")
        case = gen(output_dir)
        test_cases.append(case)
        print(f"  ✓ {case['path']}")

    # Write manifest
    manifest = {
        "schema_version": "evaluation.v1",
        "generated_by": "OCP",
        "test_cases": test_cases,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Generated {len(test_cases)} test cases")
    print(f"✓ Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    exit(main())
