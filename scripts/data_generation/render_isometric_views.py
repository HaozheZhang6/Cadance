#!/usr/bin/env python
"""Render isometric PNG views from STEP files using CadQuery renderer."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run_renderer(python_bin: Path, renderer_py: Path, step_path: Path, out_dir: Path) -> bool:
    payload = {
        "step_path": str(step_path),
        "output_dir": str(out_dir),
        "views": [
            {"name": "isometric"},
        ],
        "config": {"background_color": "white", "width": 900, "height": 700},
    }
    proc = subprocess.run(
        [str(python_bin), str(renderer_py)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", type=Path, help="Single STEP file")
    parser.add_argument("--step-dir", type=Path, help="Directory of STEP files")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed/isometric"),
        help="Output directory for PNG views",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    python_bin = Path(sys.executable)
    renderer_py = repo_root / "tools" / "cadquery" / "renderer.py"

    args.out_dir.mkdir(parents=True, exist_ok=True)

    steps: list[Path] = []
    if args.step:
        steps = [args.step]
    elif args.step_dir:
        steps = sorted(args.step_dir.glob("*.step"))
    else:
        raise SystemExit("--step or --step-dir required")

    ok = 0
    for step_path in steps:
        if _run_renderer(python_bin, renderer_py, step_path, args.out_dir):
            ok += 1

    print(json.dumps({"processed": len(steps), "ok": ok, "out_dir": str(args.out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
