#!/usr/bin/env python3
"""Convert ground truth CadQuery models to ops_program.v1 benchmark JSON.

Usage:
    # Full batch (LLM + CQ execution)
    uv run python -m scripts.data_generation.convert_gt_to_ops

    # Single file
    uv run python -m scripts.data_generation.convert_gt_to_ops --file brass_spacer_tube

    # Geometry-only (no LLM decomposition)
    uv run python -m scripts.data_generation.convert_gt_to_ops --no-llm

    # Parse + LLM only (no CadQuery execution)
    uv run python -m scripts.data_generation.convert_gt_to_ops --no-execute

    # Limit + resume
    uv run python -m scripts.data_generation.convert_gt_to_ops --limit 5 --skip-existing
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scripts.data_generation.runner import print_summary, run_batch


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert GT CadQuery models to ops_program.v1 benchmark JSON",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("data/raw_data/models"),
        help="Directory containing GT .py files (default: data/raw_data/models)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/benchmark"),
        help="Output directory for JSON files (default: data/benchmark)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip files that already have output JSON (default: True)",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Re-process all files even if output exists",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM decomposition (geometry + metadata only)",
    )
    parser.add_argument(
        "--no-execute",
        action="store_true",
        help="Skip CadQuery execution (parse + LLM only)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N files (0=all)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Process only files matching this substring",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse files and show what would be processed",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Render isometric PNG screenshot for each benchmark",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.models_dir.is_dir():
        print(f"Error: models dir not found: {args.models_dir}", file=sys.stderr)
        return 1

    if args.dry_run:
        from scripts.data_generation.parser import parse_all_gt_files

        models = parse_all_gt_files(args.models_dir)
        if args.file:
            models = [
                m
                for m in models
                if args.file in m.path.name or args.file in m.part_name
            ]
        if args.limit > 0:
            models = models[: args.limit]
        print(f"Would process {len(models)} files:")
        for m in models:
            print(f"  {m.path.name} -> {m.part_name} (#{m.part_number})")
        return 0

    # Setup LLM client
    llm_client = None
    if not args.no_llm:
        from src.agents.llm import LLMClient

        llm_client = LLMClient()

    results = run_batch(
        models_dir=args.models_dir,
        output_dir=args.output_dir,
        llm_client=llm_client,
        skip_existing=args.skip_existing,
        no_llm=args.no_llm,
        no_execute=args.no_execute,
        limit=args.limit,
        file_filter=args.file,
        render_screenshots=args.screenshots,
    )

    print_summary(results)
    return 0 if all(r.success for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
