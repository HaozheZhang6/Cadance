"""Upload a stratified external bench batch (fusion360 + deepcad) to HF.

Picks N verified rows per data_source from verified_parts.csv (both
gt_norm_step_path and norm_cq_code_path filled), renders cadrille 4-view
composite via render_step_normalized, and pushes to HF with a schema
compatible with bench/test/run_test.py.

Schema (subset of synth bench — no qa_pairs / iso_tags / difficulty):
    stem, data_source, family, difficulty, base_plane, split,
    feature_tags (json str), feature_count, ops_used (json str),
    gt_code, composite_png (HF Image)

Run on workspace (needs verified_parts.csv + VTK):
    uv sync --extra vision
    uv run python bench/upload_external.py \
        --repo Hula0401/cad_external_bench \
        --n-fusion 50 --n-deepcad 50

Then bench anywhere (no VTK needed):
    uv run python bench/test/run_test.py \
        --repo Hula0401/cad_external_bench --split test_iid --limit 100 \
        --model gpt-4o
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "data_generation"))


def build_rows(
    n_fusion: int, n_deepcad: int, seed: int = 42, verified_csv: str | None = None
) -> list[dict]:
    import pandas as pd
    from render_normalized_views import render_step_normalized

    from bench.metrics import extract_features

    csv_path = Path(verified_csv or ROOT / "data/data_generation/verified_parts.csv")
    if not csv_path.exists():
        raise SystemExit(f"verified_parts.csv not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df = df[
        df.gt_norm_step_path.notna()
        & (df.gt_norm_step_path != "")
        & df.norm_cq_code_path.notna()
        & (df.norm_cq_code_path != "")
    ]
    print(f"verified pool: {len(df)} rows (both norm paths filled)")
    for src in ["fusion360", "deepcad"]:
        print(f"  {src}: {(df.data_source == src).sum()}")

    rows: list[dict] = []
    for src, n in [("fusion360", n_fusion), ("deepcad", n_deepcad)]:
        if n <= 0:
            continue
        sub = df[df.data_source == src]
        if sub.empty:
            print(f"  SKIP {src} — no verified rows")
            continue
        picked = sub.sample(min(n, len(sub)), random_state=seed)
        print(f"\nRendering {len(picked)} {src} samples ...")

        for i, (_, s) in enumerate(picked.iterrows()):
            step_rel = s["gt_norm_step_path"]
            code_rel = s["norm_cq_code_path"]
            step_abs = ROOT / step_rel
            code_abs = ROOT / code_rel
            if not (step_abs.exists() and code_abs.exists()):
                print(f"  [{i + 1}/{len(picked)}] SKIP {s['stem']} — files missing")
                continue

            try:
                with tempfile.TemporaryDirectory() as tmp:
                    paths = render_step_normalized(str(step_abs), tmp)
                    comp_bytes = Path(paths["composite"]).read_bytes()
            except Exception as e:
                print(f"  [{i + 1}/{len(picked)}] SKIP {s['stem']} — render fail: {e}")
                continue

            gt_code = code_abs.read_text()
            feat = extract_features(gt_code)
            rows.append(
                {
                    "stem": s["stem"],
                    "data_source": src,
                    "family": src,  # placeholder (run_test.py groups by family)
                    "difficulty": "na",
                    "base_plane": "XY",
                    "split": "test_iid",
                    "feature_tags": json.dumps(feat),
                    "feature_count": sum(1 for v in feat.values() if v),
                    "ops_used": "[]",
                    "gt_code": gt_code,
                    "composite_png": comp_bytes,
                }
            )
            if (i + 1) % 10 == 0:
                print(f"  [{i + 1}/{len(picked)}] ok")
        print(f"{src}: {sum(1 for r in rows if r['data_source'] == src)} rows built")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Hula0401/cad_external_bench")
    ap.add_argument("--n-fusion", type=int, default=50)
    ap.add_argument("--n-deepcad", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verified-csv", default=None)
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env", override=False)
    except ImportError:
        pass
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN not set")

    rows = build_rows(
        args.n_fusion, args.n_deepcad, seed=args.seed, verified_csv=args.verified_csv
    )
    if not rows:
        raise SystemExit("No rows built")

    from datasets import Dataset, DatasetDict, Image
    from PIL import Image as PILImage

    for r in rows:
        r["composite_png"] = PILImage.open(io.BytesIO(r["composite_png"]))
    ds = Dataset.from_list(rows).cast_column("composite_png", Image())
    dd = DatasetDict({"test_iid": ds})

    print(f"\nPushing {len(rows)} rows to {args.repo} ...")
    dd.push_to_hub(
        args.repo,
        token=token,
        commit_message=(
            f"external bench: {args.n_fusion}F+{args.n_deepcad}D verified samples"
        ),
    )
    print(f"Done → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
