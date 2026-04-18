#!/usr/bin/env python
"""Render orthographic CAD drawings (SVG) from STEP files.

Usage:
  uv run python scripts/data_generation/render_orthographic_drawings.py --step /path/to/part.step
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo src/ is on path when running as a script.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cad_drawing.orthographic import OrthographicConfig, render_orthographic_from_step  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, required=True, help="STEP file path")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed/orthographic"),
        help="Output directory for SVG drawings",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Convert SVG outputs to PNG using cairosvg if available",
    )
    args = parser.parse_args()

    config = OrthographicConfig()
    outputs = render_orthographic_from_step(args.step, args.out_dir, config)
    if args.png and outputs:
        try:
            import cairosvg
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"cairosvg not available: {exc}") from exc
        for svg_path in outputs:
            png_path = svg_path.with_suffix(".png")
            cairosvg.svg2png(url=str(svg_path), write_to=str(png_path))
    print("\n".join(str(p) for p in outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
