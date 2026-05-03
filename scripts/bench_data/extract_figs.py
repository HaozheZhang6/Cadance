#!/usr/bin/env python3
"""For each bench-data/<slug>/raw.pdf:
   1. pdftoppm to PNG (first 12 pages, 100 DPI) → pages/page-NN.png
   2. pdfimages to PNG (all raster) → imgs/img-NNN.png, then drop tiny ones (<50KB)
"""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/references/bench-data"
MAX_PAGES = 12
MIN_IMG_BYTES = 50_000  # drop logos/icons


def process_one(slug_dir: Path) -> str:
    pdf = slug_dir / "raw.pdf"
    if not pdf.exists():
        return f"SKIP {slug_dir.name} (no raw.pdf)"
    pages = slug_dir / "pages"
    imgs = slug_dir / "imgs"
    pages.mkdir(exist_ok=True)
    imgs.mkdir(exist_ok=True)

    # 1) page renders
    if not any(pages.iterdir()):
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "100", "-f", "1", "-l", str(MAX_PAGES),
                 str(pdf), str(pages / "page")],
                check=True, capture_output=True, timeout=120,
            )
        except subprocess.CalledProcessError as e:
            return f"FAIL pages {slug_dir.name} {e.stderr.decode()[:120]}"
        except subprocess.TimeoutExpired:
            return f"FAIL pages {slug_dir.name} timeout"

    # 2) raster image extraction (best-effort; some PDFs vector-only → 0 imgs)
    if not any(imgs.iterdir()):
        try:
            subprocess.run(
                ["pdfimages", "-png", str(pdf), str(imgs / "img")],
                check=True, capture_output=True, timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        # filter tiny images
        for f in list(imgs.iterdir()):
            try:
                if f.stat().st_size < MIN_IMG_BYTES:
                    f.unlink()
            except FileNotFoundError:
                pass

    np = len(list(pages.glob("*.png")))
    ni = len(list(imgs.glob("*.png")))
    return f"OK   {slug_dir.name} pages={np} imgs={ni}"


def main() -> int:
    dirs = sorted([d for d in OUT.iterdir() if d.is_dir()])
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(process_one, d): d.name for d in dirs}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            print(r, file=sys.stderr)
    print(f"\n=== {len(results)} processed ===", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
