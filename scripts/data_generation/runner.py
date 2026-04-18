"""Batch orchestration for GT -> ops_program.v1 conversion."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.data_generation.decomposer import decompose_cadquery_to_operations
from scripts.data_generation.parser import GTModelFile, parse_all_gt_files
from scripts.data_generation.schema import (
    build_ops_program,
    infer_stock,
    output_filename,
)

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    source_file: str
    success: bool
    output_path: str | None = None
    geometry_props: dict[str, Any] | None = None
    num_operations: int = 0
    error: str | None = None
    elapsed_ms: float = 0.0


def _setup_gateway(timeout: float = 60.0):
    from src.tools.gateway.backends.subprocess_cadquery import SubprocessCadQueryBackend
    from src.tools.gateway.gateway import ToolGateway

    gw = ToolGateway()
    gw.register("cadquery", SubprocessCadQueryBackend(timeout_seconds=timeout))
    return gw


def _execute_gt_code(
    gateway, cadquery_code: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Execute GT code, return (geometry_props, step_path)."""
    result = gateway.execute("cadquery", cadquery_code)
    if result.success:
        return result.geometry_props, result.step_path
    logger.warning("CQ execution failed: %s", result.error_message)
    return None, None


def _render_screenshot(
    step_path: str,
    output_dir: Path,
    part_slug: str,
    gateway=None,
) -> str | None:
    """Render isometric PNG from STEP file. Returns path or None."""
    from src.cad.intent_decomposition.utils.visualization import (
        STANDARD_3D_VIEWS,
        render_step_to_3d_images,
    )

    try:
        iso_views = [v for v in STANDARD_3D_VIEWS if v.get("name") == "isometric"]
        result_paths = render_step_to_3d_images(
            step_path=Path(step_path),
            output_dir=output_dir,
            views=iso_views or [{"name": "isometric", "roll": -35.0, "elevation": -30.0, "zoom": 1.2}],
        )
        if "isometric" in result_paths:
            # Rename to match benchmark naming
            src = result_paths["isometric"]
            dst = output_dir / f"{part_slug}_iso{src.suffix}"
            if src != dst:
                src.rename(dst)
            logger.info("Screenshot: %s", dst.name)
            return str(dst)
    except Exception as e:
        logger.warning("Screenshot render failed: %s", e)
    return None


def convert_single(
    model: GTModelFile,
    output_dir: Path,
    llm_client=None,
    gateway=None,
    skip_existing: bool = True,
    no_llm: bool = False,
    no_execute: bool = False,
    render_screenshots: bool = False,
) -> ConversionResult:
    fname = output_filename(model)
    out_path = output_dir / fname

    if skip_existing and out_path.exists():
        logger.info("SKIP (exists): %s", fname)
        return ConversionResult(
            source_file=model.path.name,
            success=True,
            output_path=str(out_path),
        )

    t0 = time.monotonic()

    # 1) Execute GT code
    geometry_props = None
    step_path = None
    if not no_execute and gateway is not None:
        geometry_props, step_path = _execute_gt_code(gateway, model.cadquery_code)
        if geometry_props is None:
            logger.warning(
                "Execution failed for %s, continuing without geometry", model.path.name
            )

    # 2) Infer stock
    stock = infer_stock(model.cadquery_code)

    # 3) LLM decomposition
    operations: list[dict[str, Any]] = []
    decomp_meta: dict[str, Any] | None = None
    if not no_llm and llm_client is not None:
        operations, decomp_meta = decompose_cadquery_to_operations(
            llm_client=llm_client,
            cadquery_code=model.cadquery_code,
            part_name=model.part_name,
            feature_comments=model.feature_comments,
        )
        # Use LLM stock suggestion if regex failed
        if not stock and decomp_meta and decomp_meta.get("stock_suggestion"):
            stock = decomp_meta["stock_suggestion"]

    # 4) Assemble JSON
    ops_program = build_ops_program(
        model=model,
        operations=operations,
        geometry_props=geometry_props,
        stock=stock,
        decomposition_meta=decomp_meta,
    )

    # 5) Save
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(ops_program, f, indent=2)

    # 6) Render isometric screenshot
    if render_screenshots and step_path and gateway is not None:
        from scripts.data_generation.schema import _slugify

        slug = _slugify(model.part_name)
        _render_screenshot(step_path, output_dir, slug, gateway)

    elapsed = (time.monotonic() - t0) * 1000

    logger.info(
        "OK: %s -> %s (%d ops, %.0fms)",
        model.path.name,
        fname,
        len(operations),
        elapsed,
    )

    return ConversionResult(
        source_file=model.path.name,
        success=True,
        output_path=str(out_path),
        geometry_props=geometry_props,
        num_operations=len(operations),
        elapsed_ms=elapsed,
    )


def run_batch(
    models_dir: Path,
    output_dir: Path,
    llm_client=None,
    skip_existing: bool = True,
    no_llm: bool = False,
    no_execute: bool = False,
    limit: int = 0,
    file_filter: str | None = None,
    render_screenshots: bool = False,
) -> list[ConversionResult]:
    models = parse_all_gt_files(models_dir)
    logger.info("Parsed %d GT model files", len(models))

    if file_filter:
        models = [
            m
            for m in models
            if file_filter in m.path.name or file_filter in m.part_name
        ]
        logger.info("Filtered to %d files matching '%s'", len(models), file_filter)

    if limit > 0:
        models = models[:limit]
        logger.info("Limited to %d files", limit)

    gateway = None
    if not no_execute:
        gateway = _setup_gateway()

    results: list[ConversionResult] = []
    for i, model in enumerate(models):
        logger.info("[%d/%d] Processing: %s", i + 1, len(models), model.path.name)
        try:
            r = convert_single(
                model=model,
                output_dir=output_dir,
                llm_client=llm_client,
                gateway=gateway,
                skip_existing=skip_existing,
                no_llm=no_llm,
                no_execute=no_execute,
                render_screenshots=render_screenshots,
            )
            results.append(r)
        except Exception as e:
            logger.error("FAIL: %s — %s", model.path.name, e)
            results.append(
                ConversionResult(
                    source_file=model.path.name,
                    success=False,
                    error=str(e),
                )
            )

    return results


def print_summary(results: list[ConversionResult]) -> None:
    total = len(results)
    ok = sum(1 for r in results if r.success)
    fail = total - ok
    with_geom = sum(1 for r in results if r.geometry_props)
    with_ops = sum(1 for r in results if r.num_operations > 0)
    total_ops = sum(r.num_operations for r in results)

    print(f"\n{'='*50}")
    print("Benchmark Generation Summary")
    print(f"{'='*50}")
    print(f"Total files:    {total}")
    print(f"Success:        {ok}")
    print(f"Failed:         {fail}")
    print(f"With geometry:  {with_geom}")
    print(f"With operations:{with_ops}")
    if with_ops:
        print(f"Avg ops/part:   {total_ops / with_ops:.1f}")
    print(f"{'='*50}")

    if fail > 0:
        print("\nFailed files:")
        for r in results:
            if not r.success:
                print(f"  {r.source_file}: {r.error}")
