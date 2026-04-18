#!/usr/bin/env python
"""Build SFT datasets for CADQuery generation.

Produces two JSONL files:
- sft_img2cq.jsonl: multi-view drawings -> CadQuery code
- sft_json2cq.jsonl: JSON description -> CadQuery code

Optionally validates CadQuery execution and exports STEP files via tools/cadquery/executor.py.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_SOURCE_CONFIG = "data/data_generation/open_source/sources.json"


@dataclass(frozen=True)
class PairSource:
    name: str
    images_dir: Path
    codes_dir: Path


@dataclass(frozen=True)
class JsonSource:
    name: str
    json_dir: Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_code(code: str) -> str:
    """Strip leading metadata/comment block for cleaner SFT targets."""
    lines = code.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line == "" or line.startswith("#"):
            idx += 1
            continue
        break
    normalized = "\n".join(lines[idx:]).strip()
    return normalized + "\n" if normalized else ""


def _code_defines_result(code: str) -> bool:
    return "result" in code


def _run_cadquery_executor(python_bin: Path, executor_py: Path, code: str, step_path: Path) -> dict:
    payload = {
        "mode": "execute",
        "code": code,
        "step_output_path": str(step_path),
    }
    process = subprocess.run(
        [str(python_bin), str(executor_py)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0 and not process.stdout:
        return {
            "success": False,
            "error_message": process.stderr.strip(),
            "error_category": "executor",
        }
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error_message": process.stdout.strip() or process.stderr.strip(),
            "error_category": "executor",
        }


def _resolve_executor_paths(root: Path) -> tuple[Path, Path]:
    executor = root / "tools" / "cadquery" / "executor.py"
    if not executor.exists():
        raise FileNotFoundError(f"CadQuery executor not found: {executor}")
    return Path(sys.executable), executor


def _load_source_config(path: Path) -> tuple[list[PairSource], list[JsonSource]]:
    if not path.exists():
        return ([], [])
    payload = json.loads(_read_text(path))
    pair_sources = []
    json_sources = []

    for entry in payload.get("pair_sources", []):
        pair_sources.append(
            PairSource(
                name=entry["name"],
                images_dir=Path(entry["images_dir"]),
                codes_dir=Path(entry["codes_dir"]),
            )
        )

    for entry in payload.get("json_sources", []):
        json_sources.append(
            JsonSource(
                name=entry["name"],
                json_dir=Path(entry["json_dir"]),
            )
        )

    return pair_sources, json_sources


def _iter_pairs(images_dir: Path, codes_dir: Path) -> Iterable[tuple[Path, Path]]:
    if not images_dir.exists() or not codes_dir.exists():
        return []
    image_map = {}
    view_priority = {"front": 0, "top": 1, "right": 2}
    for ext in ("*.png", "*.svg"):
        for p in images_dir.glob(ext):
            stem = p.stem
            base = stem
            view = None
            for suffix in ("_front", "_top", "_right"):
                if stem.endswith(suffix):
                    base = stem[: -len(suffix)]
                    view = suffix[1:]
                    break
            if base in image_map and view is not None:
                existing = image_map[base]
                existing_view = None
                for suffix in ("_front", "_top", "_right"):
                    if existing.stem.endswith(suffix):
                        existing_view = suffix[1:]
                        break
                if existing_view is not None and view_priority[view] >= view_priority.get(existing_view, 99):
                    continue
            image_map[base] = p
    code_map = {p.stem: p for p in codes_dir.glob("*.py")}
    common = sorted(set(image_map) & set(code_map))
    return [(image_map[stem], code_map[stem]) for stem in common]


def _iter_json(json_dir: Path) -> Iterable[Path]:
    if not json_dir.exists():
        return []
    return sorted(json_dir.glob("*.json"))


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_img2cq(
    sources: list[PairSource],
    out_path: Path,
    python_bin: Path | None,
    executor_py: Path | None,
    step_dir: Path | None,
    keep_failed: bool,
) -> dict:
    total = 0
    kept = 0
    skipped = 0

    _ensure_dir(out_path.parent)
    if step_dir is not None:
        _ensure_dir(step_dir)

    with out_path.open("w", encoding="utf-8") as handle:
        for source in sources:
            for image_path, code_path in _iter_pairs(source.images_dir, source.codes_dir):
                total += 1
                code = _normalize_code(_read_text(code_path))
                if not code or not _code_defines_result(code):
                    skipped += 1
                    continue

                entry = {
                    "id": image_path.stem,
                    "task": "IMG2CQ",
                    "source": source.name,
                    "image": str(image_path),
                    "output": code,
                }

                if python_bin is not None and executor_py is not None and step_dir is not None:
                    step_path = step_dir / f"{image_path.stem}.step"
                    result = _run_cadquery_executor(python_bin, executor_py, code, step_path)
                    if not result.get("success"):
                        if keep_failed:
                            entry["cadquery_error"] = {
                                "category": result.get("error_category"),
                                "message": result.get("error_message"),
                            }
                        else:
                            skipped += 1
                            continue
                    else:
                        entry["step_path"] = result.get("step_path")
                        entry["geometry_props"] = result.get("geometry_props")

                handle.write(json.dumps(entry) + "\n")
                kept += 1

    return {"total": total, "kept": kept, "skipped": skipped}


def _extract_json_code(payload: dict) -> str | None:
    if "cadquery_code" in payload and isinstance(payload["cadquery_code"], str):
        return payload["cadquery_code"]
    if "cadquery_path" in payload and isinstance(payload["cadquery_path"], str):
        path = Path(payload["cadquery_path"]).expanduser()
        if path.exists():
            return _read_text(path)
    return None


def build_json2cq(
    sources: list[JsonSource],
    out_path: Path,
    python_bin: Path | None,
    executor_py: Path | None,
    step_dir: Path | None,
    keep_failed: bool,
) -> dict:
    total = 0
    kept = 0
    skipped = 0

    _ensure_dir(out_path.parent)
    if step_dir is not None:
        _ensure_dir(step_dir)

    with out_path.open("w", encoding="utf-8") as handle:
        for source in sources:
            for json_path in _iter_json(source.json_dir):
                total += 1
                payload = json.loads(_read_text(json_path))
                code = _extract_json_code(payload)
                if code is None:
                    skipped += 1
                    continue

                code = _normalize_code(code)
                if not code or not _code_defines_result(code):
                    skipped += 1
                    continue

                entry = {
                    "id": json_path.stem,
                    "task": "JSON2CQ",
                    "source": source.name,
                    "input": payload,
                    "output": code,
                }

                if python_bin is not None and executor_py is not None and step_dir is not None:
                    step_path = step_dir / f"{json_path.stem}.step"
                    result = _run_cadquery_executor(python_bin, executor_py, code, step_path)
                    if not result.get("success"):
                        if keep_failed:
                            entry["cadquery_error"] = {
                                "category": result.get("error_category"),
                                "message": result.get("error_message"),
                            }
                        else:
                            skipped += 1
                            continue
                    else:
                        entry["step_path"] = result.get("step_path")
                        entry["geometry_props"] = result.get("geometry_props")

                handle.write(json.dumps(entry) + "\n")
                kept += 1

    return {"total": total, "kept": kept, "skipped": skipped}


def _default_pair_sources(root: Path) -> list[PairSource]:
    return [
        PairSource(
            name="local_raw",
            images_dir=root / "data" / "raw_data" / "drawings",
            codes_dir=root / "data" / "raw_data" / "models",
        )
    ]


def _default_json_sources(root: Path) -> list[JsonSource]:
    return [
        JsonSource(
            name="local_raw",
            json_dir=root / "data" / "raw_data" / "json",
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed"),
        help="Output directory for JSONL files and steps.",
    )
    parser.add_argument(
        "--source-config",
        type=Path,
        default=Path(DEFAULT_SOURCE_CONFIG),
        help="Optional JSON config for additional open-source sources.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Execute CadQuery code and export STEP using tools/cadquery executor.",
    )
    parser.add_argument(
        "--keep-failed",
        action="store_true",
        help="Keep entries even when CadQuery execution fails.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]

    pair_sources, json_sources = _load_source_config(args.source_config)
    pair_sources = _default_pair_sources(repo_root) + pair_sources
    json_sources = _default_json_sources(repo_root) + json_sources

    python_bin = None
    executor_py = None
    step_dir = None
    if args.validate:
        python_bin, executor_py = _resolve_executor_paths(repo_root)
        step_dir = args.out_dir / "steps"

    img2cq_path = args.out_dir / "sft_img2cq.jsonl"
    json2cq_path = args.out_dir / "sft_json2cq.jsonl"

    img_stats = build_img2cq(
        sources=pair_sources,
        out_path=img2cq_path,
        python_bin=python_bin,
        executor_py=executor_py,
        step_dir=step_dir,
        keep_failed=args.keep_failed,
    )
    json_stats = build_json2cq(
        sources=json_sources,
        out_path=json2cq_path,
        python_bin=python_bin,
        executor_py=executor_py,
        step_dir=step_dir,
        keep_failed=args.keep_failed,
    )

    summary = {
        "img2cq": img_stats,
        "json2cq": json_stats,
        "out_dir": str(args.out_dir),
        "validated": args.validate,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
