#!/usr/bin/env python
"""Render a 3D view from a CadQuery script for comparison with 2D drawings.

Uses tools/cadquery/.venv to run executor and renderer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_code(code: str) -> str:
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


def _run_json_script(python_bin: Path, script: Path, payload: dict) -> dict:
    process = subprocess.run(
        [str(python_bin), str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0 and not process.stdout:
        return {"success": False, "error_message": process.stderr.strip()}
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error_message": process.stdout.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("data/raw_data/models/20251218_033650_brass_spacer_tube_v1.py"),
        help="CadQuery script to render.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed/example_render"),
        help="Output directory for STEP and PNG.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    executor_py = repo_root / "tools" / "cadquery" / "executor.py"
    renderer_py = repo_root / "tools" / "cadquery" / "renderer.py"

    python_bin = Path(sys.executable)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    code = _normalize_code(_read_text(args.model))
    step_path = args.out_dir / f"{args.model.stem}.step"

    exec_payload = {
        "mode": "execute",
        "code": code,
        "step_output_path": str(step_path),
    }
    exec_result = _run_json_script(python_bin, executor_py, exec_payload)
    if not exec_result.get("success"):
        print(json.dumps(exec_result, indent=2))
        return 1

    render_payload = {
        "step_path": str(step_path),
        "output_dir": str(args.out_dir),
        "views": [
            {"name": "isometric"},
            {"name": "front", "roll": 0, "elevation": 0},
        ],
        "config": {"background_color": "white", "width": 900, "height": 700},
    }
    render_result = _run_json_script(python_bin, renderer_py, render_payload)
    print(json.dumps(render_result, indent=2))
    return 0 if render_result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
