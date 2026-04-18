#!/usr/bin/env python
"""CadQuery executor - runs in isolated venv.

Standalone script, no imports from main cadance codebase.
Receives JSON on stdin, writes JSON to stdout.

Supports two modes:
1. "execute" (default) - Execute CadQuery code, return geometry props
2. "iou" - Execute two codes, compute Intersection over Union

Input JSON schema (execute mode):
{
    "mode": "execute",  # optional, default
    "code": "import cadquery as cq\\nresult = cq.Workplane('XY').box(10,20,30)",
    "step_output_path": "/tmp/result.step"  # optional
}

Input JSON schema (iou mode):
{
    "mode": "iou",
    "generated_code": "import cadquery as cq\\nresult = ...",
    "ground_truth_code": "import cadquery as cq\\nresult = ..."
}

Output JSON schema (execute mode):
{
    "success": true/false,
    "geometry_props": {"volume": ..., "face_count": ..., ...},
    "step_path": "/tmp/result.step" or null,
    "error_category": "none/timeout/crash/validation/syntax/geometry/unknown",
    "error_message": null or string,
    "execution_time_ms": float
}

Output JSON schema (iou mode):
{
    "success": true/false,
    "iou_score": float (0.0-1.0),
    "iou_result": {
        "intersection_volume": float,
        "union_volume": float,
        "generated_volume": float,
        "ground_truth_volume": float
    },
    "generated_props": {...},
    "ground_truth_props": {...},
    "error_category": "none/...",
    "error_message": null or string,
    "execution_time_ms": float
}
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from typing import Any


def extract_geometry_props(workplane: Any) -> dict[str, Any]:
    """Extract geometry properties from CadQuery workplane.

    Args:
        workplane: CadQuery Workplane object with geometry.

    Returns:
        Dict with volume, face_count, edge_count, vertex_count, bounding_box, solid_count.
    """
    shape = workplane.val()

    # Count solids (detect disconnected geometry)
    solid_count = 1
    if hasattr(shape, "Solids"):
        solids = shape.Solids()
        if solids:
            solid_count = len(solids)

    volume = shape.Volume()
    faces = shape.Faces()
    edges = shape.Edges()
    vertices = shape.Vertices()

    bb = shape.BoundingBox()

    return {
        "volume": round(volume, 2),
        "face_count": len(faces),
        "edge_count": len(edges),
        "vertex_count": len(vertices),
        "bounding_box": {
            "xlen": round(bb.xlen, 2),
            "ylen": round(bb.ylen, 2),
            "zlen": round(bb.zlen, 2),
        },
        "solid_count": solid_count,
    }


def export_step(workplane: Any, output_path: str) -> str:
    """Export workplane to STEP file.

    Args:
        workplane: CadQuery Workplane object.
        output_path: Path to write STEP file.

    Returns:
        Path to created file.

    Raises:
        RuntimeError: If export fails or file not created.
    """
    import cadquery as cq

    cq.exporters.export(workplane, output_path, "STEP")

    if not os.path.exists(output_path):
        raise RuntimeError(f"STEP export failed: {output_path} not created")

    return output_path


def _extract_solid(shape: Any) -> Any:
    """Extract a Solid from a shape, handling Compound objects.

    CadQuery operations like shell() can return a Compound containing a Solid.
    This function extracts the Solid for boolean operations.

    Args:
        shape: CadQuery shape (Solid, Compound, or None)

    Returns:
        Solid if extraction succeeds, None otherwise.
    """
    import cadquery as cq

    if shape is None:
        return None

    # Already a Solid - return as-is
    if isinstance(shape, cq.Solid):
        return shape

    # Compound - try to extract Solid(s)
    if isinstance(shape, cq.Compound):
        solids = shape.Solids()
        if solids:
            if len(solids) == 1:
                return solids[0]
            else:
                # Fuse multiple solids
                result = solids[0]
                for solid in solids[1:]:
                    result = result.fuse(solid)
                return result
        return None

    # Unknown type - try to use as-is
    return shape


def compute_iou(
    generated_code: str,
    ground_truth_code: str,
) -> dict[str, Any]:
    """Execute both codes and compute IoU.

    Args:
        generated_code: CadQuery code for generated geometry (must define 'result')
        ground_truth_code: CadQuery code for ground truth (must define 'result')

    Returns:
        Dict with IoU score, component volumes, and geometry props.

    Raises:
        ValueError: If geometries invalid or boolean ops fail.
    """
    import cadquery as cq

    start = time.perf_counter()

    # Execute generated code
    gen_namespace: dict[str, Any] = {"cq": cq}
    exec(generated_code, gen_namespace)  # noqa: S102
    if "result" not in gen_namespace:
        raise ValueError("generated_code must define 'result' variable")
    gen_result = gen_namespace["result"]

    # Execute ground truth code
    gt_namespace: dict[str, Any] = {"cq": cq}
    exec(ground_truth_code, gt_namespace)  # noqa: S102
    if "result" not in gt_namespace:
        raise ValueError("ground_truth_code must define 'result' variable")
    gt_result = gt_namespace["result"]

    # Extract geometry props
    gen_props = extract_geometry_props(gen_result)
    gt_props = extract_geometry_props(gt_result)

    # Extract solids for boolean operations
    gen_val = gen_result.val() if hasattr(gen_result, "val") else gen_result
    gt_val = gt_result.val() if hasattr(gt_result, "val") else gt_result

    gen_solid = _extract_solid(gen_val)
    gt_solid = _extract_solid(gt_val)

    if gen_solid is None or gt_solid is None:
        raise ValueError("Cannot compute IoU: failed to extract solids")

    # Get individual volumes
    gen_volume = gen_solid.Volume()
    gt_volume = gt_solid.Volume()

    if gen_volume <= 0 or gt_volume <= 0:
        raise ValueError(f"Invalid volumes: gen={gen_volume}, gt={gt_volume}")

    # Boolean operations for IoU
    intersection = gen_solid.intersect(gt_solid)
    union = gen_solid.fuse(gt_solid)

    intersection_vol = intersection.Volume()
    union_vol = union.Volume()

    # Compute IoU
    if union_vol <= 0:
        iou_score = 0.0
    else:
        iou_score = intersection_vol / union_vol

    # Clamp to valid range
    iou_score = max(0.0, min(1.0, iou_score))

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "iou_score": round(iou_score, 4),
        "intersection_volume": round(intersection_vol, 2),
        "union_volume": round(union_vol, 2),
        "generated_volume": round(gen_volume, 2),
        "ground_truth_volume": round(gt_volume, 2),
        "generated_props": gen_props,
        "ground_truth_props": gt_props,
        "execution_time_ms": round(elapsed_ms, 2),
    }


def execute_code(code: str, step_output_path: str | None = None) -> dict[str, Any]:
    """Execute CadQuery code and extract results.

    Args:
        code: CadQuery code to execute (must set 'result' variable).
        step_output_path: Optional path to export STEP file.

    Returns:
        Result dict matching ExecutionResult.to_dict() schema.
    """
    import cadquery as cq

    start = time.perf_counter()

    namespace: dict[str, Any] = {"cq": cq}

    try:
        exec(code, namespace)  # noqa: S102
    except SyntaxError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "geometry_props": {},
            "step_path": None,
            "error_category": "syntax",
            "error_message": f"SyntaxError: {e}",
            "execution_time_ms": round(elapsed_ms, 2),
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "geometry_props": {},
            "step_path": None,
            "error_category": "crash",
            "error_message": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            "execution_time_ms": round(elapsed_ms, 2),
        }

    if "result" not in namespace:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "geometry_props": {},
            "step_path": None,
            "error_category": "validation",
            "error_message": "Code must define 'result' variable",
            "execution_time_ms": round(elapsed_ms, 2),
        }

    result_obj = namespace["result"]

    try:
        geometry_props = extract_geometry_props(result_obj)
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "geometry_props": {},
            "step_path": None,
            "error_category": "geometry",
            "error_message": f"Geometry extraction failed: {e}",
            "execution_time_ms": round(elapsed_ms, 2),
        }

    step_path = None
    if step_output_path:
        try:
            step_path = export_step(result_obj, step_output_path)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "success": False,
                "geometry_props": geometry_props,
                "step_path": None,
                "error_category": "geometry",
                "error_message": f"STEP export failed: {e}",
                "execution_time_ms": round(elapsed_ms, 2),
            }

    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "success": True,
        "geometry_props": geometry_props,
        "step_path": step_path,
        "error_category": "none",
        "error_message": None,
        "execution_time_ms": round(elapsed_ms, 2),
    }


def main() -> int:
    """Entry point: read JSON from stdin, execute, write JSON to stdout."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        result = {
            "success": False,
            "geometry_props": {},
            "step_path": None,
            "error_category": "validation",
            "error_message": f"Invalid input JSON: {e}",
            "execution_time_ms": 0.0,
        }
        json.dump(result, sys.stdout)
        return 1

    mode = input_data.get("mode", "execute")

    if mode == "iou":
        # IoU computation mode
        generated_code = input_data.get("generated_code", "")
        ground_truth_code = input_data.get("ground_truth_code", "")

        if not generated_code or not ground_truth_code:
            result = {
                "success": False,
                "iou_score": None,
                "iou_result": None,
                "error_category": "validation",
                "error_message": "IoU mode requires 'generated_code' and 'ground_truth_code'",
                "execution_time_ms": 0.0,
            }
            json.dump(result, sys.stdout)
            return 1

        try:
            iou_result = compute_iou(generated_code, ground_truth_code)
            result = {
                "success": True,
                "iou_score": iou_result["iou_score"],
                "iou_result": {
                    "intersection_volume": iou_result["intersection_volume"],
                    "union_volume": iou_result["union_volume"],
                    "generated_volume": iou_result["generated_volume"],
                    "ground_truth_volume": iou_result["ground_truth_volume"],
                },
                "generated_props": iou_result["generated_props"],
                "ground_truth_props": iou_result["ground_truth_props"],
                "error_category": "none",
                "error_message": None,
                "execution_time_ms": iou_result["execution_time_ms"],
            }
        except SyntaxError as e:
            result = {
                "success": False,
                "iou_score": None,
                "iou_result": None,
                "error_category": "syntax",
                "error_message": f"SyntaxError: {e}",
                "execution_time_ms": 0.0,
            }
        except ValueError as e:
            result = {
                "success": False,
                "iou_score": None,
                "iou_result": None,
                "error_category": "validation",
                "error_message": str(e),
                "execution_time_ms": 0.0,
            }
        except Exception as e:
            result = {
                "success": False,
                "iou_score": None,
                "iou_result": None,
                "error_category": "crash",
                "error_message": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
                "execution_time_ms": 0.0,
            }

        json.dump(result, sys.stdout)
        return 0 if result["success"] else 1

    # Default: execute mode
    code = input_data.get("code", "")
    step_output_path = input_data.get("step_output_path")

    if not code:
        result = {
            "success": False,
            "geometry_props": {},
            "step_path": None,
            "error_category": "validation",
            "error_message": "Missing 'code' field in input",
            "execution_time_ms": 0.0,
        }
        json.dump(result, sys.stdout)
        return 1

    result = execute_code(code, step_output_path)
    json.dump(result, sys.stdout)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
