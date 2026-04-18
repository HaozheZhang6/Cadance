#!/usr/bin/env python
"""CadQuery 3D renderer - runs in isolated venv.

Standalone script for rendering STEP files to PNG using cadquery.vis.show().
Provides 3D rendered views with lighting/shading as backup to SVG pipeline.

Receives JSON on stdin, writes JSON to stdout.

Input JSON schema:
{
    "step_path": "/path/to/file.step",
    "output_dir": "/path/to/output",
    "views": [
        {"name": "isometric", "roll": -35, "elevation": -30, "zoom": 1.2},
        ...
    ],
    "config": {
        "background_color": "white",
        "width": 800,
        "height": 600
    }
}

Output JSON schema:
{
    "success": true/false,
    "png_paths": ["/path/to/output/file_isometric.png", ...],
    "error_message": null or string
}
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def compute_camera_settings(solid) -> dict:
    """Compute optimal camera settings based on geometry bounding box.

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

    # Base zoom: larger models need lower zoom
    reference_size = 100.0
    base_zoom = 1.2 * (reference_size / max(diagonal, 1.0))
    zoom = max(0.5, min(3.0, base_zoom))

    # Determine roll based on which horizontal axis is longest
    if bb.xlen >= bb.ylen:
        roll = -35
    else:
        roll = -55

    # Adjust elevation based on aspect ratio
    height_ratio = bb.zlen / max(longest, 1.0)
    if height_ratio > 1.5:
        elevation = -20
    elif height_ratio < 0.3:
        elevation = -45
    else:
        elevation = -30

    return {
        "roll": roll,
        "elevation": elevation,
        "zoom": zoom,
    }


def render_step_to_png(
    step_path: Path,
    output_dir: Path,
    views: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[Path]:
    """Render STEP file to PNG images using 3D visualization.

    Args:
        step_path: Path to STEP file.
        output_dir: Directory to save PNG images.
        views: List of view configurations.
        config: Render configuration (width, height, background).

    Returns:
        List of paths to generated PNG files.
    """
    import cadquery as cq
    from cadquery.vis import show

    # Load STEP file
    result = cq.importers.importStep(str(step_path))
    solid = result.val()

    width = config.get("width", 800)
    height = config.get("height", 600)

    # Get auto camera settings based on geometry
    auto_camera = compute_camera_settings(solid)

    # Extract stem from STEP filename for PNG naming
    stem = step_path.stem

    png_paths = []
    for view in views:
        name = view.get("name", "view")
        # Use provided values or auto-computed defaults
        roll = view.get("roll", auto_camera["roll"])
        elevation = view.get("elevation", auto_camera["elevation"])
        zoom = view.get("zoom", auto_camera["zoom"])

        png_path = output_dir / f"{stem}_{name}_3d.png"

        show(
            result,
            screenshot=str(png_path),
            interact=False,
            width=width,
            height=height,
            roll=roll,
            elevation=elevation,
            zoom=zoom,
        )

        if png_path.exists():
            png_paths.append(png_path)

    return png_paths


def main() -> int:
    """Entry point: read JSON from stdin, render, write JSON to stdout."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        result = {
            "success": False,
            "png_paths": [],
            "error_message": f"Invalid input JSON: {e}",
        }
        json.dump(result, sys.stdout)
        return 1

    step_path = Path(input_data.get("step_path", ""))
    output_dir = Path(input_data.get("output_dir", ""))
    views = input_data.get("views", [])
    config = input_data.get("config", {})

    if not step_path.exists():
        result = {
            "success": False,
            "png_paths": [],
            "error_message": f"STEP file not found: {step_path}",
        }
        json.dump(result, sys.stdout)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        png_paths = render_step_to_png(step_path, output_dir, views, config)
        result = {
            "success": True,
            "png_paths": [str(p) for p in png_paths],
            "error_message": None,
        }
    except Exception as e:
        result = {
            "success": False,
            "png_paths": [],
            "error_message": f"{type(e).__name__}: {e}",
        }

    json.dump(result, sys.stdout)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
