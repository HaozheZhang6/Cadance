#!/usr/bin/env python
"""Ingest Fusion 360 Gallery dataset files into a local open-source layout.

This script does NOT convert Fusion programs to CadQuery.
It stages the raw program JSON files and builds a manifest for later conversion.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _find_json_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Root directory of the Fusion 360 Gallery dataset (extracted).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/data_generation/open_source/fusion360_gallery"),
        help="Output directory for staged files.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy JSON files instead of creating a manifest with original paths.",
    )
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    raw_dir = output_dir / "json_raw"
    _ensure_dir(output_dir)
    _ensure_dir(raw_dir)

    json_files = _find_json_files(input_dir)
    manifest_path = output_dir / "fusion360_manifest.jsonl"

    with manifest_path.open("w", encoding="utf-8") as handle:
        for idx, path in enumerate(json_files):
            rel = path.relative_to(input_dir)
            entry = {
                "id": f"fusion360_{idx:08d}",
                "source": "fusion360_gallery",
                "relative_path": str(rel),
                "original_path": str(path),
            }
            if args.copy:
                dest = raw_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                entry["staged_path"] = str(dest)
            handle.write(json.dumps(entry) + "\n")

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "json_files": len(json_files),
        "manifest": str(manifest_path),
        "copied": args.copy,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
