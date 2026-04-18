#!/usr/bin/env python3
"""Download GenCAD-Code from HuggingFace and convert to SFT JSONL format.

Source: https://huggingface.co/datasets/CADCODER/GenCAD-Code
163K (image → CadQuery code) pairs, 448×448 isometric renders.

Produces:
  <out-dir>/images/<split>/<deepcad_id>.jpg   — raw images
  <out-dir>/sft_gencad_img2cq.jsonl           — messages-format JSONL

JSONL schema matches assemble_sft.py output:
  id, task, split, messages[system/user/assistant]

Usage:
  uv run python scripts/data_generation/download_gencad.py \\
    --out-dir data/gencad \\
    --limit 1000          # omit for full 163K
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

EXPORT_STEP_SUFFIX = "\nresult = solid\nresult.val().exportStep('output.step')\n"


def _normalise_gencad_code(code: str) -> str:
    """Normalise GenCAD-Code script to match our pipeline convention.

    GenCAD scripts end with ``solid = solidN``.  We need:
    1. ``result = solid`` alias so the variable name matches our pipeline.
    2. ``result.val().exportStep('output.step')`` so the script exports STEP.

    Idempotent — safe to call on already-normalised code.
    """
    if "exportStep" in code:
        return code
    return code.rstrip() + EXPORT_STEP_SUFFIX


SYSTEM_PROMPT = (
    "You are a CadQuery expert. Given an isometric rendering of a mechanical part, "
    "write CadQuery Python code that reproduces the geometry. "
    "Output ONLY Python code."
)

HF_DATASET = "CADCODER/GenCAD-Code"
SPLITS = ("train", "validation", "test")
# HuggingFace uses "validation"; normalise to "val" in output
_SPLIT_MAP = {"train": "train", "validation": "val", "test": "test"}


def download_and_convert(
    out_dir: Path,
    limit: int | None = None,
    splits: tuple[str, ...] = SPLITS,
    hf_cache_dir: Path | None = None,
) -> dict:
    """Download GenCAD-Code and write SFT JSONL.

    Args:
        out_dir: root output directory
        limit: max rows per split (None = all)
        splits: which HF splits to process
        hf_cache_dir: optional HuggingFace cache directory

    Returns:
        Summary dict with per-split counts.
    """
    from datasets import load_dataset  # lazy import

    img_root = out_dir / "images"
    img_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "sft_gencad_img2cq.jsonl"

    summary: dict[str, int] = {"total": 0, "written": 0, "error": 0}
    split_counts: dict[str, int] = {}

    kwargs: dict = {}
    if hf_cache_dir:
        kwargs["cache_dir"] = str(hf_cache_dir)

    print(f"Loading {HF_DATASET} ...")
    ds = load_dataset(HF_DATASET, **kwargs)

    with jsonl_path.open("w", encoding="utf-8") as out_f:
        for split_name in splits:
            if split_name not in ds:
                print(f"  Split '{split_name}' not found, skipping.")
                continue

            split_ds = ds[split_name]
            n = len(split_ds) if limit is None else min(limit, len(split_ds))
            out_split = _SPLIT_MAP.get(split_name, split_name)
            split_counts[out_split] = 0

            print(f"  Processing {split_name}: {n}/{len(split_ds)} rows ...")

            img_split_dir = img_root / split_name
            img_split_dir.mkdir(parents=True, exist_ok=True)

            for i, row in enumerate(split_ds):
                if i >= n:
                    break
                summary["total"] += 1

                deepcad_id: str = row["deepcad_id"]
                # Normalise to our pipeline convention:
                #   rename `solid` → `result`, append exportStep call
                raw_code: str = row["cadquery"]
                code = _normalise_gencad_code(raw_code)
                image = row["image"]  # PIL.Image

                # Save image (deepcad_id may contain '/' subdirs)
                img_path = img_split_dir / f"{deepcad_id}.jpg"
                img_path.parent.mkdir(parents=True, exist_ok=True)
                if not img_path.exists():
                    try:
                        image.save(str(img_path), format="JPEG", quality=90)
                    except Exception as exc:  # noqa: BLE001
                        print(f"    ERROR saving image {deepcad_id}: {exc}")
                        summary["error"] += 1
                        continue

                entry = {
                    "id": deepcad_id,
                    "task": "IMG2CQ",
                    "source": "gencad",
                    "split": out_split,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "image", "path": str(img_path)}
                            ],
                        },
                        {"role": "assistant", "content": code},
                    ],
                }
                out_f.write(json.dumps(entry) + "\n")
                summary["written"] += 1
                split_counts[out_split] = split_counts.get(out_split, 0) + 1

                if (i + 1) % 5000 == 0:
                    print(f"    {i + 1}/{n} done ...")

    summary["splits"] = split_counts  # type: ignore[assignment]
    return summary


def postprocess_jsonl(jsonl_path: Path) -> dict:
    """Post-process an existing sft_gencad_img2cq.jsonl to normalise code.

    Rewrites the file in-place, appending the exportStep suffix to any
    assistant message that doesn't already have it.

    Returns counts of rows fixed vs already-ok.
    """
    import tempfile

    fixed = already_ok = 0
    tmp = jsonl_path.with_suffix(".tmp")
    with jsonl_path.open(encoding="utf-8") as src, tmp.open(
        "w", encoding="utf-8"
    ) as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            msgs = row.get("messages", [])
            for msg in msgs:
                if msg.get("role") == "assistant":
                    orig = msg["content"]
                    norm = _normalise_gencad_code(orig)
                    if norm != orig:
                        msg["content"] = norm
                        fixed += 1
                    else:
                        already_ok += 1
            dst.write(json.dumps(row) + "\n")
    tmp.replace(jsonl_path)
    return {"fixed": fixed, "already_ok": already_ok}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "data/gencad",
        help="Output directory (default: data/gencad)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max rows per split (default: all ~163K)",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=list(SPLITS),
        choices=list(SPLITS),
        help="Which splits to download",
    )
    parser.add_argument(
        "--hf-cache-dir",
        type=Path,
        default=None,
        help="HuggingFace cache directory",
    )
    parser.add_argument(
        "--postprocess-only",
        action="store_true",
        help="Skip download; only normalise existing JSONL (add exportStep)",
    )
    args = parser.parse_args()

    if args.postprocess_only:
        jsonl = args.out_dir / "sft_gencad_img2cq.jsonl"
        if not jsonl.exists():
            print(f"ERROR: {jsonl} not found. Run without --postprocess-only first.")
            return 1
        print(f"Post-processing {jsonl} ...")
        result = postprocess_jsonl(jsonl)
        print(json.dumps(result, indent=2))
        return 0

    result = download_and_convert(
        out_dir=args.out_dir,
        limit=args.limit,
        splits=tuple(args.splits),
        hf_cache_dir=args.hf_cache_dir,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
