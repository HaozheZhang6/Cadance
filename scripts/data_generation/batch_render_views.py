#!/usr/bin/env python
"""Batch render front/right/top/iso views from STEP files for dataset generation.

Outputs PNGs sized to --max-px (default 600px max dimension) so that Claude
can comfortably process --batch-size parts (4 views each) per call.

Usage:
  # Test: first 20 STEP files
  uv run python scripts/data_generation/batch_render_views.py \
      --step-dir data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools \
      --out-dir data/processed/views_dataset \
      --limit 20

  # Full run
  uv run python scripts/data_generation/batch_render_views.py \
      --step-dir data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools \
      --out-dir data/processed/views_dataset
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cad_drawing.orthographic import (  # noqa: E402
    OrthographicConfig,
    render_orthographic_from_step,
)

VIEWS = ("front", "right", "top", "iso")


def _svg_dims(svg_path: Path) -> tuple[float, float]:
    """Return (width, height) from SVG root attributes."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    w = float(root.get("width", "1"))
    h = float(root.get("height", "1"))
    return w, h


def _svg_to_png(svg_path: Path, png_path: Path, max_px: int) -> None:
    import cairosvg

    w, h = _svg_dims(svg_path)
    if w >= h:
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=max_px)
    else:
        cairosvg.svg2png(
            url=str(svg_path), write_to=str(png_path), output_height=max_px
        )


def _render_part(
    step_path: Path,
    out_dir: Path,
    config: OrthographicConfig,
    max_px: int,
) -> dict | None:
    """Render all views for one STEP file. Returns info dict or None on failure."""
    try:
        svgs = render_orthographic_from_step(step_path, out_dir, config)
    except Exception as exc:
        return {"stem": step_path.stem, "error": str(exc)}

    pngs = {}
    for svg_path in svgs:
        view = svg_path.stem.split("_")[-1]
        png_path = svg_path.with_suffix(".png")
        try:
            _svg_to_png(svg_path, png_path, max_px)
            pngs[view] = png_path.name
        except Exception as exc:
            return {"stem": step_path.stem, "error": f"png {view}: {exc}"}
        svg_path.unlink()  # remove intermediate SVG

    return {"stem": step_path.stem, "views": pngs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--step-dir",
        type=Path,
        required=True,
        help="Directory containing .step files",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed/views_dataset"),
        help="Output root directory",
    )
    parser.add_argument(
        "--max-px",
        type=int,
        default=600,
        help="Max PNG dimension in pixels (default: 600)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Parts per batch folder (default: 10)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most this many STEP files (0 = all)",
    )
    args = parser.parse_args()

    step_files = sorted(args.step_dir.glob("*.step"))
    if not step_files:
        step_files = sorted(args.step_dir.glob("*.STEP"))
    if args.limit > 0:
        step_files = step_files[: args.limit]

    print(f"Found {len(step_files)} STEP files → batches of {args.batch_size}")

    config = OrthographicConfig()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    batches: list[dict] = []
    current_batch: list[dict] = []
    batch_idx = 0

    for i, step_path in enumerate(step_files):
        batch_dir = args.out_dir / f"batch_{batch_idx:04d}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        t0 = time.perf_counter()
        info = _render_part(step_path, batch_dir, config, args.max_px)
        elapsed = time.perf_counter() - t0

        if info and "error" not in info:
            ok += 1
            current_batch.append(info)
            status = "ok"
        else:
            fail += 1
            status = f"FAIL: {info.get('error', '?') if info else 'None'}"

        print(f"  [{i+1}/{len(step_files)}] {step_path.name}  {status}  {elapsed:.1f}s")

        if len(current_batch) >= args.batch_size:
            manifest = {"batch": batch_idx, "parts": current_batch}
            (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
            batches.append(manifest)
            current_batch = []
            batch_idx += 1

    # Flush remaining
    if current_batch:
        batch_dir = args.out_dir / f"batch_{batch_idx:04d}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"batch": batch_idx, "parts": current_batch}
        (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        batches.append(manifest)

    summary = {
        "total": len(step_files),
        "ok": ok,
        "failed": fail,
        "batches": len(batches),
        "batch_size": args.batch_size,
        "max_px": args.max_px,
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
