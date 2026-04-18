#!/usr/bin/env python3
"""Generate isometric PNG images for all evaluation suite samples.

Creates a visual catalog of all ground truth CAD models for quick reference.
Images are saved alongside each sample's spec.json and ground_truth.py.

Usage:
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_images.py
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_images.py --level 1
    uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_images.py --test L1_02
"""

import argparse
import math
from pathlib import Path

import cadquery as cq
from cadquery.vis import show

# Image settings
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 600

# Base isometric camera settings
BASE_ELEVATION = -30  # Looking down at 30 degrees
BASE_ROLL = -35  # Standard isometric roll


def compute_camera_settings(solid) -> dict:
    """Compute optimal camera settings based on geometry bounding box.

    The algorithm:
    1. Get bounding box dimensions
    2. Determine the best viewing angle based on aspect ratio
    3. Calculate zoom to fit the model in frame

    Args:
        solid: CadQuery solid object.

    Returns:
        Dict with roll, elevation, zoom settings.
    """
    bb = solid.BoundingBox()
    dims = sorted([bb.xlen, bb.ylen, bb.zlen], reverse=True)
    longest, middle, shortest = dims

    # Calculate diagonal for zoom estimation
    diagonal = math.sqrt(bb.xlen**2 + bb.ylen**2 + bb.zlen**2)

    # Base zoom: larger models need lower zoom, smaller need higher
    # Calibrated for ~100mm reference size to fill frame nicely
    reference_size = 100.0
    base_zoom = 1.2 * (reference_size / max(diagonal, 1.0))

    # Clamp zoom to reasonable range
    zoom = max(0.5, min(3.0, base_zoom))

    # Determine roll based on which horizontal axis is longest
    # This orients the model so the longest dimension is displayed prominently
    if bb.xlen >= bb.ylen:
        # X is longer - standard isometric view
        roll = -35
    else:
        # Y is longer - rotate to show Y axis better
        roll = -55

    # Adjust elevation based on aspect ratio (tall vs flat)
    height_ratio = bb.zlen / max(longest, 1.0)
    if height_ratio > 1.5:
        # Tall object - look more from the side
        elevation = -20
    elif height_ratio < 0.3:
        # Flat object - look more from above
        elevation = -45
    else:
        # Standard proportions
        elevation = -30

    return {
        "roll": roll,
        "elevation": elevation,
        "zoom": zoom,
    }


def render_ground_truth(ground_truth_path: Path, output_path: Path) -> bool:
    """Execute ground_truth.py and render to PNG with smart camera.

    Args:
        ground_truth_path: Path to ground_truth.py file.
        output_path: Path for output PNG file.

    Returns:
        True if successful, False otherwise.
    """
    namespace = {"cq": cq}

    try:
        code = ground_truth_path.read_text()
        exec(code, namespace)

        if "result" not in namespace:
            print("  ERROR: No 'result' variable")
            return False

        result = namespace["result"]
        solid = result.val()

        # Compute optimal camera settings for this geometry
        camera = compute_camera_settings(solid)

        # Render with smart camera view
        show(
            result,
            screenshot=str(output_path),
            interact=False,
            width=IMAGE_WIDTH,
            height=IMAGE_HEIGHT,
            **camera,
        )

        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        return False


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
        description="Generate PNG images from ground truth CadQuery code.",
    )
    parser.add_argument("--level", "-l", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--test", "-t", type=str, help="e.g., L1_02")
    args = parser.parse_args()

    base_dir = Path(__file__).parent

    test_dirs = find_test_dirs(base_dir, args.level, args.test)

    if not test_dirs:
        print("No test cases found")
        return 1

    print(f"Generating images for {len(test_dirs)} test case(s)\n")

    success = 0
    failed = 0

    for test_dir in test_dirs:
        ground_truth_path = test_dir / "ground_truth.py"

        # Extract test ID from directory name (e.g., "L1_02_cylinder" -> "L1_02")
        parts = test_dir.name.split("_")
        test_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else test_dir.name

        # Save image in the sample directory alongside spec.json and ground_truth.py
        output_path = test_dir / "preview.png"

        print(f"{test_id}...", end=" ", flush=True)
        if render_ground_truth(ground_truth_path, output_path):
            print(f"OK -> {output_path.relative_to(base_dir)}")
            success += 1
        else:
            failed += 1

    print(f"\nGenerated: {success}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
