"""Per-family montage builder for batch_audit_apr18 visual audit.

For each family, pick 2 samples per difficulty (=6 samples), composite their
4-view PNGs into a single labeled image. One montage per family lets the
auditor scan all 80 families efficiently.

Usage:
    uv run python -m scripts.data_generation.cad_synth.build_audit_montages \
        --batch batch_audit_apr18 --out /tmp/audit_montages
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/data_generation/generated_data/fusion360"


def load_samples(batch_name: str) -> dict:
    """Return {family: {difficulty: [(stem, sample_dir), ...]}}."""
    pat = re.compile(r"^synth_(?P<fam>.+)_(?P<idx>\d+)_s\d+$")
    out: dict = defaultdict(lambda: defaultdict(list))
    for d in sorted(DATA_DIR.glob("synth_*")):
        m = pat.match(d.name)
        if not m:
            continue
        sample_dir = d / f"verified_{batch_name}"
        if not sample_dir.is_dir():
            continue
        meta_path = sample_dir / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        fam = meta.get("family", m.group("fam"))
        diff = meta.get("difficulty", "easy")
        out[fam][diff].append((d.name, sample_dir))
    return out


def build_montage(family: str, by_diff: dict, out_path: Path, per_diff: int = 2):
    """3 rows (easy/med/hard) × per_diff cols × 4 sub-views per cell."""
    diffs = ["easy", "medium", "hard"]
    cell_w = 300  # width of one composite.png after resize
    cell_h = 300
    pad = 12
    label_h = 28
    title_h = 36

    cols = per_diff
    rows = len(diffs)
    img_w = cols * cell_w + (cols + 1) * pad
    img_h = title_h + rows * (cell_h + label_h) + (rows + 1) * pad

    canvas = Image.new("RGB", (img_w, img_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_label = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = ImageFont.load_default()

    draw.text(
        (pad, 6),
        f"{family}  ({sum(len(by_diff.get(d, [])) for d in diffs)} samples)",
        fill=(20, 20, 20),
        font=font_title,
    )

    for r, diff in enumerate(diffs):
        samples = by_diff.get(diff, [])[:per_diff]
        for c in range(cols):
            x0 = pad + c * (cell_w + pad)
            y0 = title_h + pad + r * (cell_h + label_h + pad)
            if c < len(samples):
                stem, sdir = samples[c]
                comp = sdir / "views" / "composite.png"
                if comp.is_file():
                    try:
                        im = Image.open(comp).convert("RGB")
                        im.thumbnail((cell_w, cell_h), Image.LANCZOS)
                        cx = x0 + (cell_w - im.width) // 2
                        cy = y0 + (cell_h - im.height) // 2
                        canvas.paste(im, (cx, cy))
                    except Exception:
                        draw.rectangle(
                            [x0, y0, x0 + cell_w, y0 + cell_h],
                            outline=(200, 0, 0),
                            width=2,
                        )
                idx = stem.split("_")[-2]
                lbl = f"{diff} #{idx}"
                draw.text(
                    (x0, y0 + cell_h + 4), lbl, fill=(60, 60, 60), font=font_label
                )
            else:
                draw.rectangle(
                    [x0, y0, x0 + cell_w, y0 + cell_h], outline=(200, 200, 200), width=1
                )
                draw.text(
                    (x0 + 8, y0 + cell_h // 2 - 8),
                    f"no {diff} samples",
                    fill=(180, 0, 0),
                    font=font_label,
                )

    canvas.save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--batch", required=True, help="batch run name (e.g. batch_audit_apr18)"
    )
    ap.add_argument("--out", required=True, help="output dir for montages")
    ap.add_argument("--per-diff", type=int, default=2)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_samples(args.batch)
    print(f"families with samples: {len(samples)}")

    for fam in sorted(samples):
        out_path = out_dir / f"{fam}.png"
        build_montage(fam, samples[fam], out_path, per_diff=args.per_diff)
        n_total = sum(len(samples[fam].get(d, [])) for d in ["easy", "medium", "hard"])
        print(f"  {fam}: {n_total} samples → {out_path.name}")


if __name__ == "__main__":
    main()
