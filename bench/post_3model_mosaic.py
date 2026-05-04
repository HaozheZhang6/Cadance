"""Build 4-col mosaic (GT, 4o, 5.3-thinking, 5.3-chat-latest) for cad_bench_200, post to Discord.

For each of 200 stems (sorted alphabetically):
  col 0 = GT composite_png (from cad_bench_200 parquet)
  col 1 = gpt-4o renders/<stem>.png
  col 2 = gpt-5.3-thinking renders/<stem>.png
  col 3 = gpt-5.3-chat-latest renders/<stem>.png

Splits into 4 chunks of 50 rows each, posts each PNG separately to Discord webhook.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

import pyarrow.parquet as pq  # noqa: E402

PARQUET_GLOB = (
    "data/hf_cache/hub/datasets--BenchCAD--cad_bench_200/snapshots/*/data/*.parquet"
)
OUT_DIR = ROOT / "data" / "data_generation" / "bench" / "from_hf" / "3model_mosaic"
MODELS = [
    ("gpt-4o", "4o"),
    ("gpt-5.3-thinking", "5.3-thinking"),
    ("gpt-5.3-chat-latest", "5.3-chat-latest"),
    ("moonshot-v1-8k-vision-preview", "kimi"),
]
CELL = 256
LABEL_W = 240
PAD = 4
CHUNK_ROWS = 50
HEADER_H = 36


def _font(s: int):
    for p in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(p, s)
        except OSError:
            continue
    return ImageFont.load_default()


def _decode(b) -> Image.Image:
    if isinstance(b, dict):
        b = b.get("bytes")
    return Image.open(io.BytesIO(b)).convert("RGB")


def _find_parquet() -> Path:
    snaps = sorted(ROOT.glob(PARQUET_GLOB))
    if not snaps:
        sys.exit("[err] cad_bench_200 parquet 不在 hf_cache, 先 load_dataset 一次")
    return snaps[-1]


def _post_discord(out_path: Path, caption: str, max_retries: int = 3) -> None:
    """POST file to Discord webhook with rate-limit-aware retry."""
    import time as _t

    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("[skip] DISCORD_WEBHOOK_URL not set", flush=True)
        return
    for attempt in range(max_retries):
        r = subprocess.run(
            [
                "curl",
                "-sS",
                "-X",
                "POST",
                "-F",
                f"file=@{out_path}",
                "-F",
                f'payload_json={{"content":{json.dumps(caption)}}}',
                url,
            ],
            capture_output=True,
            text=True,
        )
        try:
            resp = json.loads(r.stdout)
        except json.JSONDecodeError:
            print(
                f"  discord error (attempt {attempt + 1}): {r.stdout[:200]}", flush=True
            )
            _t.sleep(3)
            continue
        if resp.get("id"):
            print(
                f"  discord: id={resp.get('id')} | "
                f"attached {[a.get('filename') for a in resp.get('attachments', [])]}",
                flush=True,
            )
            _t.sleep(2)  # Be polite, avoid burst rate-limit
            return
        # 429 rate-limited or other error
        retry_after = resp.get("retry_after", 5)
        print(
            f"  discord rate-limit/err (attempt {attempt + 1}): {str(resp)[:200]} "
            f"(sleeping {retry_after}s)",
            flush=True,
        )
        _t.sleep(retry_after)
    print(f"  discord GAVE UP after {max_retries} attempts", flush=True)


def main() -> int:
    pq_path = _find_parquet()
    print(f"[in]  {pq_path.relative_to(ROOT)}", flush=True)
    t = pq.read_table(
        pq_path, columns=["stem", "family", "difficulty", "composite_png"]
    )
    rows = sorted(t.to_pylist(), key=lambda r: r["stem"])
    print(f"[in]  {len(rows)} stems", flush=True)

    gen_renders: dict[str, dict[str, Path]] = {}
    for model, _ in MODELS:
        rd = ROOT / "results" / "img2cq" / model / "renders"
        gen_renders[model] = {p.stem: p for p in rd.glob("*.png")}
        print(f"[render] {model}: {len(gen_renders[model])} PNG", flush=True)

    n_cols = 1 + len(MODELS)  # GT + each model
    W = LABEL_W + n_cols * (CELL + PAD) + PAD
    row_h = CELL + PAD
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n_chunks = (len(rows) + CHUNK_ROWS - 1) // CHUNK_ROWS
    print(f"[out] {n_chunks} chunks of up to {CHUNK_ROWS} rows", flush=True)

    f_h = _font(15)
    f_l = _font(11)
    f_s = _font(8)
    headers = ["GT"] + [label for _, label in MODELS]

    for ci in range(n_chunks):
        start = ci * CHUNK_ROWS
        end = min(start + CHUNK_ROWS, len(rows))
        chunk = rows[start:end]
        H = HEADER_H + len(chunk) * row_h + PAD
        canvas = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(canvas)

        for ki, h in enumerate(headers):
            x = LABEL_W + ki * (CELL + PAD) + CELL // 2 - 30
            draw.text((x, 10), h, fill="black", font=f_h)

        for ri, r in enumerate(chunk):
            y = HEADER_H + ri * row_h
            stem = r["stem"]
            draw.text((PAD, y + CELL // 2 - 18), stem[:30], fill="black", font=f_s)
            draw.text((PAD, y + CELL // 2), r["family"][:24], fill="#444", font=f_l)
            draw.text((PAD, y + CELL // 2 + 14), r["difficulty"], fill="#666", font=f_s)
            try:
                gt = _decode(r["composite_png"]).resize((CELL, CELL), Image.LANCZOS)
            except Exception:
                gt = Image.new("RGB", (CELL, CELL), "#eee")
            canvas.paste(gt, (LABEL_W, y))
            for mi, (model, _) in enumerate(MODELS):
                x = LABEL_W + (mi + 1) * (CELL + PAD)
                p = gen_renders[model].get(stem)
                if p and p.exists():
                    img = (
                        Image.open(p).convert("RGB").resize((CELL, CELL), Image.LANCZOS)
                    )
                else:
                    img = Image.new("RGB", (CELL, CELL), "#eee")
                    dl = ImageDraw.Draw(img)
                    dl.text(
                        (CELL // 2 - 32, CELL // 2 - 6),
                        "(no render)",
                        fill="#999",
                        font=f_s,
                    )
                canvas.paste(img, (x, y))

        out_path = OUT_DIR / f"chunk_{ci + 1:02d}_of_{n_chunks:02d}.png"
        canvas.save(out_path, optimize=True)
        size_mb = out_path.stat().st_size / 1e6
        print(
            f"[chunk {ci + 1}/{n_chunks}] rows {start + 1}-{end} → "
            f"{out_path.relative_to(ROOT)} ({size_mb:.1f} MB)",
            flush=True,
        )
        cap = (
            f"cad_bench_200 mosaic chunk {ci + 1}/{n_chunks} "
            f"rows {start + 1}-{end} of {len(rows)} - col: "
            + " | ".join(headers)
        )
        _post_discord(out_path, cap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
