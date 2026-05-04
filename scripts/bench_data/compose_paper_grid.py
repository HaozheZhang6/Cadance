"""Compose a paper × figure grid from extracted page renders.

For each paper with `digest.md` + `pages/page-NN.png`, parses the Figures
table in the digest to get the page numbers of the first ≤5 figures (skipping
tables), grabs the corresponding page render, and tiles them into one big
PNG: rows = papers, cols = Figure 1..5.

Output: paper/references/bench-data/_grids/grid_{NN}.png  (split into chunks)
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "paper/references/bench-data"
OUT = BENCH / "_grids"
OUT.mkdir(exist_ok=True)


def _parse_digest(p: Path) -> tuple[str, list[int]]:
    """Return (slug, list of page numbers for figures only, in order)."""
    text = p.read_text(errors="replace")
    slug = p.parent.name
    pages: list[int] = []
    in_table = False
    for line in text.splitlines():
        if "## Figures" in line:
            in_table = True
            continue
        if in_table and line.startswith("##"):
            break
        if in_table and line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            num, page, typ = cells[0], cells[1], cells[2]
            if not page.isdigit() or not num.isdigit():
                continue
            # exclude pure-table rows; everything else (figure/qualitative/
            # bar chart/scatter/flow/data-stats/...) is a figure for our grid.
            if typ.lower().strip() == "table":
                continue
            pages.append(int(page))
    return slug, pages[:5]


def _load_thumb(p: Path, target_w: int) -> Image.Image | None:
    if not p.exists():
        return None
    img = Image.open(p).convert("RGB")
    ratio = target_w / img.width
    return img.resize((target_w, int(img.height * ratio)), Image.LANCZOS)


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("/System/Library/Fonts/SFNS.ttf",
                 "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def compose(papers: list[tuple[str, list[int]]], out: Path,
            cell_w: int = 360, label_w: int = 180,
            cols: int = 5) -> None:
    """One image per page. Each row: [label] [Fig1] [Fig2] ... [Fig5]."""
    cell_h = int(cell_w * 1.30)  # rough page aspect
    pad = 8
    header_h = 38
    row_h = cell_h + pad
    img_w = label_w + cols * (cell_w + pad) + pad
    img_h = header_h + len(papers) * row_h + pad

    canvas = Image.new("RGB", (img_w, img_h), "white")
    d = ImageDraw.Draw(canvas)

    fnt_h = _font(20)
    fnt_l = _font(14)

    # column headers
    d.text((label_w + pad, 8), "Paper", fill="#222", font=fnt_h)
    for c in range(cols):
        x = label_w + pad + c * (cell_w + pad)
        d.text((x + cell_w // 2 - 30, 8), f"Figure {c+1}", fill="#222", font=fnt_h)

    for r, (slug, pages) in enumerate(papers):
        y = header_h + r * row_h
        # paper label
        d.rectangle([(0, y), (label_w, y + cell_h)], outline="#ccc", width=1)
        # wrap label every 18 chars
        label = slug.replace("_", " ")
        words = label.split()
        lines = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 > 22:
                lines.append(cur.strip())
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        for k, ln in enumerate(lines[:5]):
            d.text((4, y + 8 + k * 18), ln, fill="#111", font=fnt_l)
        d.text((4, y + cell_h - 22), f"({len(pages)} fig)", fill="#888", font=fnt_l)

        # figure cells
        slug_dir = BENCH / slug / "pages"
        for c in range(cols):
            x = label_w + pad + c * (cell_w + pad)
            d.rectangle([(x, y), (x + cell_w, y + cell_h)], outline="#ddd")
            if c < len(pages):
                p = slug_dir / f"page-{pages[c]:02d}.png"
                thumb = _load_thumb(p, cell_w - 6)
                if thumb is not None:
                    canvas.paste(thumb, (x + 3, y + 3))
                    d.text((x + 6, y + cell_h - 22), f"p{pages[c]}",
                           fill="#666", font=fnt_l)
            else:
                d.text((x + cell_w // 2 - 10, y + cell_h // 2 - 10),
                       "—", fill="#bbb", font=fnt_h)

    canvas.save(out, optimize=True)
    print(f"saved -> {out}  ({img_w}x{img_h})")


def main() -> None:
    digests = sorted(BENCH.glob("*/digest.md"))
    parsed = [_parse_digest(d) for d in digests]
    parsed = [(s, p) for s, p in parsed if p]   # only keep papers with ≥1 figure
    print(f"papers with figures: {len(parsed)}")

    chunk = 13
    for i in range(0, len(parsed), chunk):
        out = OUT / f"grid_{i//chunk + 1:02d}.png"
        compose(parsed[i : i + chunk], out)


if __name__ == "__main__":
    main()
