#!/usr/bin/env python3
"""Generate spec.json files from ground truth CadQuery code.

Runs each ground_truth.py file and extracts BREP geometry properties
to generate the corresponding spec.json.

Uses the SAME extraction logic (src.cad.geometry_properties) as the
evaluation pipeline, ensuring specs match what CadQuery/OCCT produces.

Usage:
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_specs.py
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_specs.py --level 1
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_specs.py --test L1_02
"""

import argparse
import json
from pathlib import Path

import cadquery as cq

from src.cad.geometry_properties import extract_geometry_properties


def run_ground_truth(ground_truth_path: Path) -> dict | None:
    """Execute ground_truth.py and extract geometry properties."""
    namespace = {"cq": cq}

    try:
        code = ground_truth_path.read_text()
        exec(code, namespace)

        if "result" not in namespace:
            print("  ERROR: No 'result' variable")
            return None

        props = extract_geometry_properties(namespace["result"])
        return props.to_spec_dict()

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def load_base_spec(test_dir: Path) -> dict:
    """Load base spec data that isn't geometry-derived."""
    spec_path = test_dir / "spec.json"

    if spec_path.exists():
        spec = json.loads(spec_path.read_text())
        for key in list(spec.keys()):
            if key.startswith("expected_"):
                del spec[key]
        return spec

    # Construct from directory name: "L1_02_cylinder" -> id="L1_02", level=1
    parts = test_dir.name.split("_")
    test_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else test_dir.name
    level = int(parts[0][1]) if parts[0].startswith("L") else 1
    name = " ".join(parts[2:]).title() if len(parts) > 2 else test_dir.name

    return {"id": test_id, "name": name, "level": level}


def generate_spec(test_dir: Path) -> bool:
    """Generate spec.json for a test case."""
    ground_truth_path = test_dir / "ground_truth.py"
    spec_path = test_dir / "spec.json"

    if not ground_truth_path.exists():
        print("  SKIP: No ground_truth.py")
        return False

    geometry_props = run_ground_truth(ground_truth_path)
    if geometry_props is None:
        return False

    spec = load_base_spec(test_dir)
    spec.update(geometry_props)
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")
    return True


def find_test_dirs(
    base_dir: Path, level: int | None, test_id: str | None
) -> list[Path]:
    """Find test case directories in train/ and eval/ subdirectories."""
    test_dirs = []

    for split in ["train", "eval"]:
        split_dir = base_dir / split
        if not split_dir.exists():
            continue

        for level_dir in sorted(split_dir.iterdir()):
            if not level_dir.is_dir() or not level_dir.name.startswith("level_"):
                continue

            try:
                dir_level = int(level_dir.name.split("_")[1])
            except (IndexError, ValueError):
                continue

            if level is not None and dir_level != level:
                continue

            for test_dir in sorted(level_dir.iterdir()):
                if not test_dir.is_dir():
                    continue

                if test_id and test_id not in test_dir.name:
                    continue

                if (test_dir / "ground_truth.py").exists():
                    test_dirs.append(test_dir)

    return test_dirs


def main():
    parser = argparse.ArgumentParser(
        description="Generate spec.json files from ground truth CadQuery code.",
    )
    parser.add_argument("--level", "-l", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--test", "-t", type=str, help="e.g., L1_02")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    test_dirs = find_test_dirs(base_dir, args.level, args.test)

    if not test_dirs:
        print("No test cases found")
        return 1

    print(f"Generating specs for {len(test_dirs)} test case(s)\n")

    success = 0
    failed = 0

    for test_dir in test_dirs:
        print(f"{test_dir.name}...", end=" ")
        if generate_spec(test_dir):
            print("OK")
            success += 1
        else:
            failed += 1

    print(f"\nGenerated: {success}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
