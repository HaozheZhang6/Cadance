#!/usr/bin/env python
"""Compare generated SVG drawings against Fusion360 PNG previews.

Requires: cairosvg, pillow, numpy (cairosvg optional; script will exit if missing).
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _rasterize_svg(svg_path: Path) -> Image.Image:
    try:
        import cairosvg
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"cairosvg not available: {exc}") from exc
    png_bytes = cairosvg.svg2png(url=str(svg_path))
    return Image.open(io.BytesIO(png_bytes)).convert("L")


def _load_png(path: Path) -> Image.Image:
    return Image.open(path).convert("L")


def _resize_to_match(a: Image.Image, b: Image.Image) -> tuple[Image.Image, Image.Image]:
    size = (min(a.size[0], b.size[0]), min(a.size[1], b.size[1]))
    return a.resize(size), b.resize(size)


def _mae(a: Image.Image, b: Image.Image) -> float:
    a_arr = np.array(a, dtype=np.float32) / 255.0
    b_arr = np.array(b, dtype=np.float32) / 255.0
    return float(np.mean(np.abs(a_arr - b_arr)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg-dir", type=Path, required=True)
    parser.add_argument("--png-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    svg_files = sorted(args.svg_dir.glob("*_front.svg"))[: args.limit]
    if not svg_files:
        print("No SVG files found")
        return 1

    rows = []
    for svg_path in svg_files:
        base = svg_path.name.replace("_front.svg", "")
        png_path = args.png_dir / f"{base}.png"
        if not png_path.exists():
            continue
        try:
            svg_img = _rasterize_svg(svg_path)
        except SystemExit as exc:
            print(exc)
            return 1
        png_img = _load_png(png_path)
        svg_img, png_img = _resize_to_match(svg_img, png_img)
        score = _mae(svg_img, png_img)
        rows.append((base, score))

    rows.sort(key=lambda x: x[1])
    for base, score in rows[:10]:
        print(f"{base} mae={score:.4f}")
    if rows:
        avg = sum(s for _, s in rows) / len(rows)
        print(f"avg mae={avg:.4f} across {len(rows)} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
