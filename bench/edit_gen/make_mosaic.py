"""Stitch per-record previews into one large mosaic for final review.

Layout: N rows × 1 col, each row = (big #num | preview image).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
FINAL = BENCH / "topup_final"


def main():
    from PIL import Image, ImageDraw, ImageFont
    previews_dir = FINAL / "previews"
    recs = [json.loads(l) for l in (FINAL / "records.jsonl").read_text().splitlines() if l]
    # Sort as in CSV (by family, difficulty)
    diff_rank = {"easy": 0, "medium": 1, "hard": 2}
    recs.sort(key=lambda r: (r["family"], diff_rank.get(r["difficulty"], 9),
                              r["edit_type"]))

    try:
        num_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
    except Exception:
        num_font = ImageFont.load_default()

    rows = []
    for idx, rec in enumerate(recs, 1):
        png_path = previews_dir / f"{rec['record_id']}.png"
        if not png_path.exists():
            continue
        img = Image.open(png_path).copy()
        # Add big #N on left
        NUM_W = 180
        new = Image.new("RGB", (NUM_W + img.width, img.height), "white")
        new.paste(img, (NUM_W, 0))
        d = ImageDraw.Draw(new)
        d.text((20, img.height // 2 - 55), f"#{idx}", fill="black",
               font=num_font)
        rows.append(new)

    if not rows:
        print("no previews found")
        return

    W = max(r.width for r in rows)
    ROW_GAP = 50
    H = sum(r.height for r in rows) + ROW_GAP * len(rows)
    canvas = Image.new("RGB", (W, H), "white")
    y = 0
    for r in rows:
        canvas.paste(r, (0, y))
        y += r.height + ROW_GAP
    out = FINAL / "preview_all.png"
    canvas.save(str(out))
    print(f"mosaic: {len(rows)} rows -> {out} ({W}×{H})")


if __name__ == "__main__":
    main()
