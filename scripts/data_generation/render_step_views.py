#!/usr/bin/env python
"""Render 4-view (front/right/top/iso) PNG screenshots of a STEP file.

Uses HLR edge projection → SVG → PIL rasterisation (no cairo/inkscape needed).

Usage:
    # Single STEP file → writes front.png right.png top.png iso.png to --out-dir
    LD_LIBRARY_PATH=/workspace/.local/lib uv run python \\
        scripts/data_generation/render_step_views.py \\
        --step path/to/part.step --out-dir /tmp/views

    # Compare raw vs generated STEP (writes raw_* and gen_* PNGs)
    LD_LIBRARY_PATH=/workspace/.local/lib uv run python \\
        scripts/data_generation/render_step_views.py \\
        --step data/data_generation/open_source/.../raw.step \\
        --gen-step data/data_generation/codex_validation/.../gen.step \\
        --out-dir /tmp/compare
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


# ---------------------------------------------------------------------------
# SVG → PIL rasteriser (handles polyline, line, text, rect)
# ---------------------------------------------------------------------------

def _svg_to_pil(svg_path: Path, scale: float = 1.0):
    """Rasterise a wire-frame SVG to a PIL Image (RGBA)."""
    from PIL import Image, ImageDraw, ImageFont

    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = "http://www.w3.org/2000/svg"

    w = int(float(root.get("width", 400)) * scale)
    h = int(float(root.get("height", 400)) * scale)
    img = Image.new("RGBA", (w, h), "white")
    draw = ImageDraw.Draw(img)

    def _col(val: str | None, default: str = "black") -> str:
        if not val or val == "none":
            return default
        return val

    def _pts(points_str: str) -> list[tuple[float, float]]:
        vals = points_str.replace(",", " ").split()
        return [(float(vals[i]) * scale, float(vals[i + 1]) * scale)
                for i in range(0, len(vals) - 1, 2)]

    stroke_w = max(1, int(scale))

    for el in root.iter():
        tag = el.tag.replace(f"{{{ns}}}", "")

        if tag == "rect":
            x = float(el.get("x", 0)) * scale
            y = float(el.get("y", 0)) * scale
            rw = float(el.get("width", w)) * scale
            rh = float(el.get("height", h)) * scale
            fill = el.get("fill", "white")
            if fill and fill != "none":
                draw.rectangle([x, y, x + rw, y + rh], fill=fill)

        elif tag == "polyline":
            pts_str = el.get("points", "")
            if not pts_str:
                continue
            pts = _pts(pts_str)
            stroke = _col(el.get("stroke"), "black")
            if len(pts) >= 2:
                draw.line(pts, fill=stroke, width=stroke_w)

        elif tag == "line":
            x1 = float(el.get("x1", 0)) * scale
            y1 = float(el.get("y1", 0)) * scale
            x2 = float(el.get("x2", 0)) * scale
            y2 = float(el.get("y2", 0)) * scale
            stroke = _col(el.get("stroke"), "black")
            draw.line([(x1, y1), (x2, y2)], fill=stroke, width=stroke_w)

        elif tag == "text":
            x = float(el.get("x", 0)) * scale
            y = float(el.get("y", 0)) * scale
            txt = (el.text or "").strip()
            if txt:
                fill = _col(el.get("fill"), "black")
                try:
                    draw.text((x, y), txt, fill=fill)
                except Exception:
                    pass

    return img


# ---------------------------------------------------------------------------
# 4-view composite
# ---------------------------------------------------------------------------

def _composite_4views(pngs: dict[str, Path], out_path: Path) -> Path:
    """Combine front/right/top/iso into a 2×2 grid PNG."""
    from PIL import Image

    order = ["front", "right", "top", "iso"]
    imgs = []
    for v in order:
        p = pngs.get(v)
        if p and p.exists():
            imgs.append(Image.open(p).convert("RGBA"))
        else:
            imgs.append(Image.new("RGBA", (400, 400), "white"))

    w = max(im.width for im in imgs)
    h = max(im.height for im in imgs)
    grid = Image.new("RGBA", (w * 2, h * 2), "white")
    positions = [(0, 0), (w, 0), (0, h), (w, h)]
    for im, pos in zip(imgs, positions):
        grid.paste(im, pos)
    grid.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_step_views(
    step_path: Path,
    out_dir: Path,
    prefix: str = "",
    composite: bool = True,
    scale: float = 0.5,
) -> dict[str, Path]:
    """Render 4 views of a STEP file → PNGs.

    Returns dict mapping view names to PNG paths.
    If composite=True, also writes a <prefix>composite.png 2×2 grid.
    """
    from cad_drawing.orthographic import render_orthographic_from_step  # noqa

    out_dir.mkdir(parents=True, exist_ok=True)
    svgs = render_orthographic_from_step(step_path, out_dir)

    result: dict[str, Path] = {}
    for svg_path in svgs:
        # svg name: <stem>_<view>.svg
        view = svg_path.stem.rsplit("_", 1)[-1]
        png_path = out_dir / f"{prefix}{view}.png"
        img = _svg_to_pil(svg_path, scale=scale)
        img.save(png_path)
        result[view] = png_path

    if composite and len(result) == 4:
        comp = out_dir / f"{prefix}composite.png"
        _composite_4views(result, comp)
        result["composite"] = comp

    # Remove intermediate SVGs
    for svg_path in svgs:
        svg_path.unlink(missing_ok=True)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Render 4-view PNGs from STEP file")
    parser.add_argument("--step", required=True, type=Path, help="Input STEP file")
    parser.add_argument("--gen-step", type=Path, default=None, help="Generated STEP (for comparison)")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory")
    parser.add_argument("--scale", type=float, default=0.5, help="Scale factor for PNG (default 0.5)")
    args = parser.parse_args()

    raw_views = render_step_views(args.step, args.out_dir, prefix="raw_", scale=args.scale)
    print(f"Raw views: {[str(p) for p in raw_views.values()]}")

    if args.gen_step:
        gen_views = render_step_views(args.gen_step, args.out_dir, prefix="gen_", scale=args.scale)
        print(f"Gen views: {[str(p) for p in gen_views.values()]}")


if __name__ == "__main__":
    main()
