"""
Assemble SFT JSONL datasets from verified_parts.csv.

Outputs:
  sft_img2cq.jsonl  -- 4-view images -> CadQuery code
  sft_json2cq.jsonl -- ops_program JSON -> CadQuery code (F360 only)

Messages format (OpenAI-compatible):
  {"id": ..., "task": ..., "source": ..., "messages": [{role, content}, ...]}
"""

import argparse
import json
import os
import sys

import pandas as pd

SYSTEM_IMG2CQ = (
    "You are a CadQuery expert. "
    "Given a 2×2 grid of normalized multi-view renders of a mechanical part "
    "(four diagonal viewpoints: [1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1]), "
    "write CadQuery Python code that reproduces the geometry. "
    "Output ONLY Python code."
)

SYSTEM_IMG2CQ_LEGACY = (
    "You are a CadQuery expert. "
    "Given orthographic views (front, right, top, isometric) of a mechanical part, "
    "write CadQuery Python code that reproduces the geometry. "
    "Output ONLY Python code."
)

SYSTEM_JSON2CQ = (
    "You are a CadQuery expert. "
    "Given a Fusion360 reconstruction JSON describing a mechanical part, "
    "write CadQuery Python code that reproduces the geometry. "
    "Output ONLY Python code."
)

SYSTEM_CORRECTION = (
    "You are a CadQuery expert. "
    "You will be shown incorrect CadQuery code for a mechanical part, "
    "the error category explaining what is wrong, and the corrected code. "
    "Learn to identify and fix this class of error."
)


def _read_cq_code(path: str) -> str:
    with open(path) as f:
        code = f.read()
    # strip the exportStep line — it's an artifact of validation, not useful for training
    lines = code.splitlines()
    filtered = [
        l
        for l in lines
        if "exportStep" not in l and "output.step" not in l
    ]
    return "\n".join(filtered).strip()


def _read_ops_json(path: str) -> str:
    with open(path) as f:
        return f.read().strip()


def _views_for(views_dir: str, prefix: str = "raw") -> tuple[list[dict], bool]:
    """
    Return (image_parts, is_normalized).

    Prefers normalized composite.png (2×2 grid, new format).
    Falls back to legacy raw_front/right/top/iso.png (old SVG format).
    """
    if not views_dir:
        return [], False
    # New normalized format: single composite 2×2 image
    composite = os.path.join(views_dir, "composite.png")
    if os.path.isfile(composite):
        return [{"type": "image", "path": composite}], True
    # Legacy SVG-based format: 4 separate orthographic views
    views = []
    for view in ("front", "right", "top", "iso"):
        p = os.path.join(views_dir, f"{prefix}_{view}.png")
        if not os.path.isfile(p):
            return [], False
        views.append({"type": "image", "path": p})
    return views, False


def build_img2cq(df: pd.DataFrame, out_path: str) -> int:
    """Build IMG2CQ JSONL from non-copy_gt rows with views."""
    genuine = df[~df["note"].str.contains("copy_gt", na=False)]
    rows = genuine[
        genuine["views_raw_dir"].notna()
        & (genuine["views_raw_dir"] != "")
        & genuine["cq_code_path"].notna()
    ].copy()

    written = 0
    skipped = 0
    with open(out_path, "w") as f:
        for _, r in rows.iterrows():
            views_dir = str(r["views_raw_dir"])
            images, is_norm = _views_for(views_dir, prefix="raw")
            if not images:
                # fall back to gen views
                images, is_norm = _views_for(str(r.get("views_gen_dir", "")), prefix="gen")
            if not images:
                skipped += 1
                continue
            # Prefer normalized CQ code when images are normalized
            norm_cq = str(r.get("norm_cq_code_path", "")) if is_norm else ""
            cq_path = norm_cq if (norm_cq and os.path.isfile(norm_cq)) else str(r["cq_code_path"])
            if not os.path.isfile(cq_path):
                skipped += 1
                continue
            code = _read_cq_code(cq_path)
            if not code:
                skipped += 1
                continue
            system = SYSTEM_IMG2CQ if is_norm else SYSTEM_IMG2CQ_LEGACY
            record = {
                "id": r["stem"],
                "task": "IMG2CQ",
                "source": str(r.get("source", "")),
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": images},
                    {"role": "assistant", "content": code},
                ],
            }
            f.write(json.dumps(record) + "\n")
            written += 1

    print(f"img2cq: {written} written, {skipped} skipped → {out_path}")
    return written


def build_json2cq(df: pd.DataFrame, out_path: str) -> int:
    """Build JSON2CQ JSONL from rows with ops_json_path (Fusion360 only)."""
    genuine = df[~df["note"].str.contains("copy_gt", na=False)]
    rows = genuine[
        genuine["ops_json_path"].notna()
        & (genuine["ops_json_path"] != "")
        & genuine["cq_code_path"].notna()
    ].copy()

    written = 0
    skipped = 0
    with open(out_path, "w") as f:
        for _, r in rows.iterrows():
            ops_path = str(r["ops_json_path"])
            if not os.path.isfile(ops_path):
                skipped += 1
                continue
            cq_path = str(r["cq_code_path"])
            if not os.path.isfile(cq_path):
                skipped += 1
                continue
            ops_json = _read_ops_json(ops_path)
            code = _read_cq_code(cq_path)
            if not ops_json or not code:
                skipped += 1
                continue
            record = {
                "id": r["stem"],
                "task": "JSON2CQ",
                "source": str(r.get("source", "")),
                "messages": [
                    {"role": "system", "content": SYSTEM_JSON2CQ},
                    {"role": "user", "content": ops_json},
                    {"role": "assistant", "content": code},
                ],
            }
            f.write(json.dumps(record) + "\n")
            written += 1

    print(f"json2cq: {written} written, {skipped} skipped → {out_path}")
    return written


def build_correction(
    verified_df: pd.DataFrame, parts_csv: str, out_path: str
) -> int:
    """Build CORRECTION JSONL: (bad_code, failure_code, good_code) triples.

    Two sources of correction pairs:
    1. _claude_fixed stems: verified_parts.csv[source_stem != ""] → look up bad code in parts.csv
    2. react-fixed stems: verified_parts.csv[bad_cq_path != ""] → bad_cq_path is direct path
    """
    parts_idx = None
    if os.path.isfile(parts_csv):
        parts = pd.read_csv(parts_csv)
        parts_idx = parts.set_index("stem")

    written = 0
    skipped = 0

    # Collect all candidate rows
    candidates = []

    # Source 1: _claude_fixed stems (source_stem → parts.csv lookup)
    if parts_idx is not None:
        fixes = verified_df[
            verified_df["source_stem"].notna() & (verified_df["source_stem"] != "")
        ]
        for _, r in fixes.iterrows():
            source_stem = str(r["source_stem"])
            good_cq_path = str(r.get("cq_code_path", ""))
            if source_stem not in parts_idx.index:
                continue
            src = parts_idx.loc[source_stem]
            if isinstance(src, pd.DataFrame):
                src = src.sort_values("iou", ascending=False).iloc[0]
            bad_cq_path = str(src.get("cq_code_path", ""))
            failure_code = str(src.get("failure_code", ""))
            candidates.append((r["stem"], good_cq_path, bad_cq_path, failure_code,
                                str(r.get("source", ""))))

    # Source 2: react-fixed stems (bad_cq_path column in verified_parts.csv)
    if "bad_cq_path" in verified_df.columns:
        react_fixes = verified_df[
            verified_df["bad_cq_path"].notna() & (verified_df["bad_cq_path"] != "")
        ]
        # Avoid duplicating stems already covered by source 1
        covered = {stem for stem, *_ in candidates}
        for _, r in react_fixes.iterrows():
            if r["stem"] in covered:
                continue
            bad_cq_path = str(r["bad_cq_path"])
            good_cq_path = str(r.get("cq_code_path", ""))
            # Get failure_code from parts_idx if available, else empty
            failure_code = ""
            if parts_idx is not None and r["stem"] in parts_idx.index:
                src = parts_idx.loc[r["stem"]]
                if isinstance(src, pd.DataFrame):
                    src = src.iloc[0]
                failure_code = str(src.get("failure_code", ""))
            candidates.append((r["stem"], good_cq_path, bad_cq_path, failure_code,
                                str(r.get("source", ""))))

    if not candidates:
        print(f"correction: 0 written (no correction pairs found) → {out_path}")
        return 0

    with open(out_path, "w") as f:
        for stem, good_cq_path, bad_cq_path, failure_code, source in candidates:
            if not os.path.isfile(bad_cq_path) or not os.path.isfile(good_cq_path):
                skipped += 1
                continue

            bad_code = _read_cq_code(bad_cq_path)
            good_code = _read_cq_code(good_cq_path)
            if not bad_code or not good_code:
                skipped += 1
                continue

            record = {
                "id": stem,
                "task": "CORRECTION",
                "source": source,
                "failure_code": failure_code,
                "messages": [
                    {"role": "system", "content": SYSTEM_CORRECTION},
                    {
                        "role": "user",
                        "content": (
                            f"# Error category: {failure_code}\n\n"
                            f"# Incorrect code:\n```python\n{bad_code}\n```\n\n"
                            "Fix the code so it produces the correct geometry."
                        ),
                    },
                    {"role": "assistant", "content": good_code},
                ],
                # DPO-ready fields
                "chosen": good_code,
                "rejected": bad_code,
            }
            f.write(json.dumps(record) + "\n")
            written += 1

    print(f"correction: {written} written, {skipped} skipped → {out_path}")
    return written


def main():
    parser = argparse.ArgumentParser(description="Assemble SFT datasets")
    parser.add_argument(
        "--verified-csv",
        default="data/data_generation/verified_parts.csv",
        help="Path to verified_parts.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="data/data_generation/sft",
        help="Output directory",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=["img2cq", "json2cq"],
        choices=["img2cq", "json2cq", "correction"],
    )
    parser.add_argument(
        "--parts-csv",
        default="data/data_generation/parts.csv",
        help="Path to parts.csv (needed for correction task)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.verified_csv):
        print(f"ERROR: {args.verified_csv} not found", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    df = pd.read_csv(args.verified_csv)
    print(f"Loaded {len(df)} records")

    stats = {}
    if "img2cq" in args.tasks:
        out = os.path.join(args.out_dir, "sft_img2cq.jsonl")
        stats["img2cq"] = build_img2cq(df, out)

    if "json2cq" in args.tasks:
        out = os.path.join(args.out_dir, "sft_json2cq.jsonl")
        stats["json2cq"] = build_json2cq(df, out)

    if "correction" in args.tasks:
        out = os.path.join(args.out_dir, "sft_correction.jsonl")
        stats["correction"] = build_correction(df, args.parts_csv, out)

    summary = {
        **stats,
        "out_dir": args.out_dir,
        "verified_csv": args.verified_csv,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
