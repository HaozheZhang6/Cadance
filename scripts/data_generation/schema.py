"""Stock inference and ops_program.v1 JSON assembly."""

from __future__ import annotations

import re
from typing import Any

from scripts.data_generation.parser import GTModelFile


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug


def infer_stock(cadquery_code: str) -> dict:
    """Infer stock geometry from the first CadQuery operation.

    Returns dict matching ops_program.v1 stock schema, or empty dict on failure.
    """
    box_m = re.search(
        r"\.box\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", cadquery_code
    )
    if box_m:
        return {
            "type": "block",
            "dimensions": {
                "x": float(box_m.group(1)),
                "y": float(box_m.group(2)),
                "z": float(box_m.group(3)),
            },
        }

    cyl_m = re.search(
        r"\.circle\(\s*([\d.]+)\s*\)\s*\.extrude\(\s*([\d.]+)\s*\)",
        cadquery_code,
    )
    if cyl_m:
        return {
            "type": "cylinder",
            "dimensions": {
                "radius": float(cyl_m.group(1)),
                "height": float(cyl_m.group(2)),
            },
        }

    poly_m = re.search(
        r"\.polygon\(\s*(\d+)\s*,\s*([\d.]+)\s*\)\s*\.extrude\(\s*([\d.]+)\s*\)",
        cadquery_code,
    )
    if poly_m:
        return {
            "type": "polygon",
            "dimensions": {
                "sides": int(poly_m.group(1)),
                "radius": float(poly_m.group(2)),
                "height": float(poly_m.group(3)),
            },
        }

    return {}


def build_ops_program(
    model: GTModelFile,
    operations: list[dict[str, Any]],
    geometry_props: dict[str, Any] | None,
    stock: dict[str, Any],
    decomposition_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble full ops_program.v1 JSON."""
    slug = _slugify(model.part_name)

    desc_parts = [model.part_name.title()]
    if model.feature_comments:
        desc_parts.append("; ".join(model.feature_comments[:3]))
    description = ". ".join(desc_parts)

    result: dict[str, Any] = {
        "schema_version": "ops_program.v1",
        "name": slug,
        "description": description,
        "units": "mm",
        "stock": stock,
        "operations": operations,
        "generated_cadquery_code": model.cadquery_code,
        "validation_passed": geometry_props is not None
        and geometry_props.get("solid_count", 0) >= 1,
    }

    if geometry_props:
        result["geometry_properties"] = geometry_props

    result["gt_metadata"] = {
        "part_number": model.part_number,
        "source_file": model.path.name,
        "generation_model": model.generation_model,
        "timestamp_utc": model.timestamp_utc,
        "version": model.version,
        "status": model.status,
    }

    if decomposition_meta:
        result["decomposition_metadata"] = decomposition_meta

    return result


def output_filename(model: GTModelFile) -> str:
    slug = _slugify(model.part_name)
    return f"{slug}_{model.part_number}.json"
