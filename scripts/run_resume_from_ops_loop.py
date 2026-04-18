#!/usr/bin/env python3
"""Loop runner for `src.cli resume --from-step from-ops`.

Creates one run directory per iteration under `data/logs/<timestamp>/` and:
- sets `VISION_SCREENSHOT_DIR` to `<run_dir>/screenshots`
- stores full command output in `<run_dir>/resume_from_ops.log`
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Continuously run resume --from-step from-ops for eval batches.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="Max iterations (0 means infinite).",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Sleep time between iterations.",
    )
    parser.add_argument(
        "--command",
        default="uv run python -m src.cli resume --from-step from-ops --only --dry-run",
        help="Command to run each iteration.",
    )
    parser.add_argument(
        "--logs-root",
        default="data/logs",
        help="Root directory for run logs.",
    )
    return parser


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _extract_pipeline_lines(stdout: str, stderr: str) -> list[str]:
    """Extract key pipeline lines for quick scan logs."""
    markers = ("[OPS_GEN]", "Vision evaluation", "LLM call log summary")
    lines: list[str] = []
    for line in (stdout + "\n" + stderr).splitlines():
        if any(marker in line for marker in markers):
            lines.append(line)
    return lines


def _write_pipeline_logs(
    *,
    run_dir: Path,
    logs_root: Path,
    iteration: int,
    exit_code: int,
    duration_seconds: float,
    pipeline_lines: list[str],
) -> tuple[Path, Path]:
    """Write per-run and global pipeline-focused logs."""
    per_run_log = run_dir / "ops_gen_pipeline.log"
    global_log = logs_root / "ops_gen_pipeline_history.log"

    header = [
        f"iteration={iteration}",
        f"run_dir={run_dir}",
        f"exit_code={exit_code}",
        f"duration_seconds={duration_seconds:.3f}",
        "",
    ]
    body = pipeline_lines or ["(no pipeline lines matched markers)"]
    per_run_log.write_text("\n".join(header + body) + "\n", encoding="utf-8")

    history_block = [
        "=" * 80,
        f"time={datetime.now().isoformat(timespec='seconds')}",
        f"iteration={iteration}",
        f"run_dir={run_dir}",
        f"exit_code={exit_code}",
        f"duration_seconds={duration_seconds:.3f}",
        "-" * 80,
        *body,
        "",
    ]
    with global_log.open("a", encoding="utf-8") as f:
        f.write("\n".join(history_block))

    return per_run_log, global_log


def _run_once(command: str, run_dir: Path, logs_root: Path, iteration: int) -> int:
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "resume_from_ops.log"

    env = os.environ.copy()
    env["VISION_SCREENSHOT_DIR"] = str(screenshots_dir)

    print(f"[run] dir={run_dir}")
    print(f"[run] screenshots={screenshots_dir}")
    print(f"[run] cmd={command}")

    started = time.time()
    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        env=env,
    )
    elapsed = time.time() - started

    combined = []
    combined.append(f"exit_code={result.returncode}")
    combined.append(f"duration_seconds={elapsed:.3f}")
    combined.append("")
    combined.append("=== STDOUT ===")
    combined.append(result.stdout or "")
    combined.append("")
    combined.append("=== STDERR ===")
    combined.append(result.stderr or "")
    log_path.write_text("\n".join(combined), encoding="utf-8")
    pipeline_lines = _extract_pipeline_lines(result.stdout or "", result.stderr or "")
    per_run_ops_log, global_ops_log = _write_pipeline_logs(
        run_dir=run_dir,
        logs_root=logs_root,
        iteration=iteration,
        exit_code=result.returncode,
        duration_seconds=elapsed,
        pipeline_lines=pipeline_lines,
    )

    print(f"[run] exit={result.returncode} duration={elapsed:.2f}s " f"log={log_path}")
    print(f"[run] ops_log={per_run_ops_log}")
    print(f"[run] ops_history={global_ops_log}")
    return result.returncode


def main() -> int:
    args = _build_parser().parse_args()
    logs_root = Path(args.logs_root)
    logs_root.mkdir(parents=True, exist_ok=True)

    run_index = 0
    while True:
        if args.max_runs > 0 and run_index >= args.max_runs:
            print(f"[done] reached max-runs={args.max_runs}")
            return 0

        run_dir = logs_root / _timestamp()
        # Ensure uniqueness for sub-second loops.
        suffix = 0
        while run_dir.exists():
            suffix += 1
            run_dir = logs_root / f"{_timestamp()}_{suffix:02d}"
        run_dir.mkdir(parents=True, exist_ok=False)

        run_index += 1
        print(f"\n=== iteration {run_index} ===")
        exit_code = _run_once(args.command, run_dir, logs_root, run_index)

        if exit_code != 0:
            print("[warn] non-zero exit; continue to next iteration")

        if args.interval_seconds > 0:
            time.sleep(args.interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
