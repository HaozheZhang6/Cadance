"""Upload a small stratified smoke batch to HF.

Picks N families × 3 difficulties = 3N samples from synth_parts.csv (accepted+production),
packs composite.png + code.py + meta into an HF Dataset, pushes to --repo.

Usage:
    uv run python bench/smoke_upload.py \
        --repo Hula0401/cad_synth_bench_smoke \
        --families bolt,bevel_gear,clevis_pin,ball_knob
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_rows(families: list[str], seed: int = 42) -> list[dict]:
    import pandas as pd

    df = pd.read_csv(ROOT / "data/data_generation/synth_parts.csv")
    df = df[(df.status == "accepted") & (df.sample_type == "production")]

    rows = []
    for fam in families:
        for diff in ("easy", "medium", "hard"):
            sub = df[(df.family == fam) & (df.difficulty == diff)]
            if sub.empty:
                print(f"  SKIP {fam}/{diff} — no samples")
                continue
            s = sub.sample(1, random_state=seed).iloc[0]

            comp_path = ROOT / s["render_dir"] / "composite.png"
            code_path = ROOT / s["code_path"]
            meta_path = ROOT / s["meta_path"]
            if not (comp_path.exists() and code_path.exists() and meta_path.exists()):
                print(f"  SKIP {s['stem']} — files missing")
                continue

            meta = json.loads(meta_path.read_text())
            feature_tags = meta.get("feature_tags", {})
            rows.append(
                {
                    "stem": s["stem"],
                    "family": s["family"],
                    "difficulty": s["difficulty"],
                    "base_plane": s["base_plane"],
                    "split": "test_iid",
                    "feature_tags": json.dumps(feature_tags),
                    "feature_count": sum(1 for v in feature_tags.values() if v),
                    "ops_used": s["ops_used"],
                    "gt_code": code_path.read_text(),
                    "composite_png": comp_path.read_bytes(),
                    "qa_pairs": json.dumps(meta.get("qa_pairs", [])),
                    "iso_tags": json.dumps(meta.get("iso_tags", {})),
                }
            )
            print(f"  + {s['stem']} ({diff})")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Hula0401/cad_synth_bench_smoke")
    ap.add_argument("--families", default="bolt,bevel_gear,clevis_pin,ball_knob")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN not set")

    families = [f.strip() for f in args.families.split(",") if f.strip()]
    print(f"Picking samples from {len(families)} families × 3 diffs ...")
    rows = build_rows(families, seed=args.seed)
    if not rows:
        raise SystemExit("No rows built")

    from datasets import Dataset, DatasetDict, Image
    from PIL import Image as PILImage

    # bytes → PIL
    for r in rows:
        r["composite_png"] = PILImage.open(io.BytesIO(r["composite_png"]))

    ds = Dataset.from_list(rows).cast_column("composite_png", Image())
    dd = DatasetDict({"test_iid": ds})
    print(f"Pushing {len(rows)} rows to {args.repo} ...")
    dd.push_to_hub(
        args.repo,
        token=token,
        commit_message=f"smoke: {len(rows)} samples ({','.join(families)})",
    )
    print(f"Done → https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
