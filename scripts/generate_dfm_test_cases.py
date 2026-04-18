#!/usr/bin/env python
"""Generate STEP files with realistic DFM violations for evaluation."""

import json
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCylinder,
)
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer


def export_step(shape, output_path: Path) -> bool:
    """Export shape to STEP file."""
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(str(output_path))
    return status == 1


def generate_golden_pass_box(output_dir: Path):
    """L1: Golden pass - simple box with good geometry."""
    box = BRepPrimAPI_MakeBox(50.0, 50.0, 20.0).Shape()

    step_path = output_dir / "L1_golden_pass.step"
    export_step(box, step_path)

    # Create ops program (no features - just base extrusion)
    ops_program = {"schema_version": "ops_program.v1", "operations": []}

    ops_path = output_dir / "L1_golden_pass_ops.json"
    with open(ops_path, "w") as f:
        json.dump(ops_program, f, indent=2)

    return {
        "name": "golden_pass_box",
        "level": 1,
        "description": "Simple box with good manufacturability (baseline)",
        "expected": {
            "status": "PASS",
            "volume": 50000.0,
            "bbox": [50.0, 50.0, 20.0],
            "violations": [],
        },
        "path": str(step_path),
        "ops_program": str(ops_path),
    }


def generate_thin_wall_violation(output_dir: Path):
    """L2: Thin wall - 0.5mm wall thickness (DFM violation)."""
    # Create thin-walled box (shell)
    outer_box = BRepPrimAPI_MakeBox(50.0, 50.0, 20.0).Shape()
    inner_box = BRepPrimAPI_MakeBox(gp_Pnt(0.5, 0.5, 0.5), 49.0, 49.0, 19.5).Shape()

    # Subtract inner from outer to create shell
    cut_op = BRepAlgoAPI_Cut(outer_box, inner_box)
    cut_op.Build()
    thin_shell = cut_op.Shape()

    step_path = output_dir / "L2_thin_wall.step"
    export_step(thin_shell, step_path)

    # Create ops program with shell operation
    ops_program = {
        "schema_version": "ops_program.v1",
        "operations": [
            {
                "primitive": "shell",
                "parameters": [{"name": "thickness", "value": 0.5, "unit": "mm"}],
            }
        ],
    }

    ops_path = output_dir / "L2_thin_wall_ops.json"
    with open(ops_path, "w") as f:
        json.dump(ops_program, f, indent=2)

    return {
        "name": "thin_wall_shell",
        "level": 2,
        "description": "Box with 0.5mm wall thickness (below 2mm threshold)",
        "expected": {
            "status": "FAIL",
            "volume": 50000.0 - 49.0 * 49.0 * 19.5,
            "bbox": [50.0, 50.0, 20.0],
            "violations": ["thin_wall"],
        },
        "path": str(step_path),
        "ops_program": str(ops_path),
    }


def generate_sharp_edge_violation(output_dir: Path):
    """L3: Sharp edge - unfilleted edges (DFM violation)."""
    # Box with sharp edges (no fillets)
    # In real manufacturing, sharp external edges are problematic
    box = BRepPrimAPI_MakeBox(50.0, 50.0, 20.0).Shape()

    step_path = output_dir / "L3_sharp_edge.step"
    export_step(box, step_path)

    # Create ops program with very small fillet (below threshold)
    ops_program = {
        "schema_version": "ops_program.v1",
        "operations": [
            {
                "primitive": "fillet",
                "parameters": [{"name": "radius", "value": 0.05, "unit": "mm"}],
            }
        ],
    }

    ops_path = output_dir / "L3_sharp_edge_ops.json"
    with open(ops_path, "w") as f:
        json.dump(ops_program, f, indent=2)

    return {
        "name": "sharp_edge_box",
        "level": 3,
        "description": "Box with unfilleted edges (sharp corners - DFM risk)",
        "expected": {
            "status": "WARN",  # Sharp edges typically warnings not blockers
            "volume": 50000.0,
            "bbox": [50.0, 50.0, 20.0],
            "violations": ["sharp_edge"],
        },
        "path": str(step_path),
        "ops_program": str(ops_path),
    }


def generate_small_hole_violation(output_dir: Path):
    """L4: Small hole - 0.3mm diameter (DFM violation)."""
    # Base box
    base = BRepPrimAPI_MakeBox(50.0, 50.0, 20.0).Shape()

    # Small hole (0.3mm diameter) - difficult to manufacture
    hole_axis = gp_Ax2(gp_Pnt(25.0, 25.0, 0.0), gp_Dir(0, 0, 1))
    small_hole = BRepPrimAPI_MakeCylinder(hole_axis, 0.15, 20.0).Shape()  # r=0.15

    # Cut hole from base
    cut_op = BRepAlgoAPI_Cut(base, small_hole)
    cut_op.Build()
    part_with_hole = cut_op.Shape()

    step_path = output_dir / "L4_small_hole.step"
    export_step(part_with_hole, step_path)

    # Create ops program with small hole operation
    ops_program = {
        "schema_version": "ops_program.v1",
        "operations": [
            {
                "primitive": "hole",
                "parameters": [
                    {"name": "diameter", "value": 0.3, "unit": "mm"},
                    {"name": "depth", "value": 20.0, "unit": "mm"},
                ],
            }
        ],
    }

    ops_path = output_dir / "L4_small_hole_ops.json"
    with open(ops_path, "w") as f:
        json.dump(ops_program, f, indent=2)

    return {
        "name": "small_hole_part",
        "level": 4,
        "description": "Part with 0.3mm diameter hole (below 1mm threshold)",
        "expected": {
            "status": "FAIL",
            "volume": 50000.0 - 3.14159 * 0.15 * 0.15 * 20.0,
            "bbox": [50.0, 50.0, 20.0],
            "violations": ["small_feature"],
        },
        "path": str(step_path),
        "ops_program": str(ops_path),
    }


def generate_complex_with_violations(output_dir: Path):
    """L5: Complex part with multiple DFM violations."""
    # Base with thin wall
    outer = BRepPrimAPI_MakeBox(60.0, 60.0, 30.0).Shape()
    inner = BRepPrimAPI_MakeBox(gp_Pnt(0.8, 0.8, 0.8), 58.4, 58.4, 29.2).Shape()

    cut1 = BRepAlgoAPI_Cut(outer, inner)
    cut1.Build()
    thin_shell = cut1.Shape()

    # Add sharp edge feature
    feature = BRepPrimAPI_MakeBox(gp_Pnt(20.0, 20.0, 30.0), 20.0, 20.0, 5.0).Shape()

    fuse_op = BRepAlgoAPI_Fuse(thin_shell, feature)
    fuse_op.Build()
    complex_part = fuse_op.Shape()

    step_path = output_dir / "L5_complex_violations.step"
    export_step(complex_part, step_path)

    # Create ops program with multiple violations
    ops_program = {
        "schema_version": "ops_program.v1",
        "operations": [
            {
                "primitive": "shell",
                "parameters": [{"name": "thickness", "value": 0.8, "unit": "mm"}],
            },
            {
                "primitive": "fillet",
                "parameters": [{"name": "radius", "value": 0.1, "unit": "mm"}],
            },
        ],
    }

    ops_path = output_dir / "L5_complex_violations_ops.json"
    with open(ops_path, "w") as f:
        json.dump(ops_program, f, indent=2)

    return {
        "name": "complex_violations",
        "level": 5,
        "description": "Complex part with thin walls (0.8mm) + sharp edges",
        "expected": {
            "status": "FAIL",
            "violations": ["thin_wall", "sharp_edge"],
        },
        "path": str(step_path),
        "ops_program": str(ops_path),
    }


def main():
    """Generate all DFM test cases."""
    output_dir = Path(__file__).parent.parent / "tests" / "dfm_test_cases"
    output_dir.mkdir(parents=True, exist_ok=True)

    generators = [
        generate_golden_pass_box,
        generate_thin_wall_violation,
        generate_sharp_edge_violation,
        generate_small_hole_violation,
        generate_complex_with_violations,
    ]

    test_cases = []
    for gen in generators:
        print(f"Generating {gen.__name__}...")
        case = gen(output_dir)
        test_cases.append(case)
        print(f"  ✓ {case['name']}: {case['path']}")

    # Write manifest
    manifest = {
        "schema_version": "dfm_evaluation.v1",
        "generated_by": "OCP",
        "description": "DFM test cases with realistic manufacturability violations",
        "test_cases": test_cases,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Generated {len(test_cases)} DFM test cases")
    print(f"✓ Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    exit(main())
