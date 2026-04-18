#!/usr/bin/env python
"""Refine hard samples using Claude: fix failed CadQuery code with geometry feedback.

Strategy:
  IoU=0 parts  → try fresh Claude generation first, then refine if still failing
  IoU>0 parts  → run multi-round self-correction with geometry diff feedback

Each refinement round feeds Claude:
  - Original Fusion360 JSON (trimmed)
  - Current failed code
  - GT vs Gen volume/bbox diff + IoU score
  - Instruction to fix

Passing parts (IoU >= 0.99) are appended to verified_pairs.jsonl.

Usage:
  LD_LIBRARY_PATH=/workspace/.local/lib uv run python \\
      scripts/data_generation/refine_hard_samples.py \\
      --run-dir data/data_generation/codex_validation/run_v2_n1000 \\
      --model claude-sonnet-4-6 --max-rounds 5 --limit 50
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_LD = "/workspace/.local/lib"
_cur = os.environ.get("LD_LIBRARY_PATH", "")
if _LD not in _cur:
    os.environ["LD_LIBRARY_PATH"] = f"{_LD}:{_cur}".strip(":")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=True)
except ImportError:
    pass

from scripts.data_generation.build_verified_pairs import (  # noqa: E402
    GT_STEP_DIR,
    IOU_THRESHOLD,
    JSON_DIR,
    STEP_SUFFIX_RE,
    _classify_complexity,
    _execute_cadquery_script,
    _generate_code_claude,
    _refine_code_with_claude_feedback,
    _repo_rel,
    _safe_json_load,
)

_IOU_THRESHOLD = IOU_THRESHOLD


def _find_gt_step(stem: str) -> Path | None:
    step_map: dict[str, list[Path]] = {}
    for sf in sorted(GT_STEP_DIR.glob("*.step")):
        m = STEP_SUFFIX_RE.match(sf.stem)
        if m:
            step_map.setdefault(m.group("base"), []).append(sf)
    cands = step_map.get(stem, [])
    return sorted(cands, key=lambda p: p.stem)[-1] if cands else None


def _load_failed_parts(run_dir: Path, min_iou: float = 0.0) -> list[dict]:
    ckpt = run_dir / "checkpoint.jsonl"
    if not ckpt.exists():
        return []
    parts = []
    for line in ckpt.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if (
            r.get("stage") == "done"
            and not r.get("iou_pass")
            and r.get("iou", 0) >= min_iou
        ):
            parts.append(r)
    # Sort: non-zero IoU first (easier wins), then zero
    return sorted(parts, key=lambda x: -x.get("iou", 0))


def _compute_iou_from_path(gt_step: Path, gen_step: Path) -> float:
    from scripts.data_generation.build_verified_pairs import _compute_iou

    iou, _ = _compute_iou(gt_step, gen_step)
    return iou


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=REPO_ROOT / "data/data_generation/codex_validation/run_v2_n1000",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Claude model for generation and refinement",
    )
    parser.add_argument("--max-rounds", type=int, default=5, dest="max_rounds")
    parser.add_argument(
        "--min-iou",
        type=float,
        default=0.0,
        dest="min_iou",
        help="Only refine parts with initial IoU >= this (0=all)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max parts (0=all)")
    parser.add_argument(
        "--verified-jsonl",
        type=Path,
        default=REPO_ROOT / "data/data_generation/verified/verified_pairs.jsonl",
        dest="verified_jsonl",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    failed = _load_failed_parts(args.run_dir, min_iou=args.min_iou)
    if args.limit > 0:
        failed = failed[: args.limit]

    if not failed:
        print("No failed parts found.")
        return 0

    print(f"Refining {len(failed)} failed parts — model={args.model}  max_rounds={args.max_rounds}")
    print(f"IoU threshold={_IOU_THRESHOLD}  run={args.run_dir.name}\n")

    refined_path = args.run_dir / "refined_checkpoint.jsonl"
    already_done: set[str] = set()
    if refined_path.exists():
        for line in refined_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    already_done.add(json.loads(line)["stem"])
                except Exception:  # noqa: BLE001
                    pass

    gen_step_dir = args.run_dir / "generated_step"
    cq_dir = args.run_dir / "cadquery"
    new_verified = 0

    for idx, part in enumerate(failed, 1):
        stem = part["stem"]
        initial_iou = part.get("iou", 0.0)

        if stem in already_done:
            print(f"[{idx}/{len(failed)}] {stem}  SKIP (already refined)")
            continue

        print(f"[{idx}/{len(failed)}] {stem}  initial_IoU={initial_iou:.4f}  complexity={part.get('complexity','?')}")

        # Load JSON
        json_path = JSON_DIR / f"{stem}.json"
        if not json_path.exists():
            print(f"  SKIP: json not found")
            continue
        try:
            json_data = _safe_json_load(json_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  SKIP: json load failed: {exc}")
            continue

        gt_step = _find_gt_step(stem)
        if gt_step is None:
            print("  SKIP: GT STEP not found")
            continue

        gen_step = gen_step_dir / f"{stem}.step"

        best_code: str | None = None
        best_iou = initial_iou
        rounds_used = 0

        # For IoU=0: try fresh Claude generation before refinement
        if initial_iou == 0.0:
            print("  IoU=0 → trying fresh generation...")
            fresh_code, fresh_err = _generate_code_claude(json_data, model=args.model)
            if fresh_code:
                ran, exec_err = _execute_cadquery_script(fresh_code, gen_step, timeout_sec=60)
                if ran:
                    fresh_iou = _compute_iou_from_path(gt_step, gen_step)
                    print(f"  Fresh gen IoU={fresh_iou:.4f}")
                    if fresh_iou >= _IOU_THRESHOLD:
                        best_code = fresh_code
                        best_iou = fresh_iou
                        rounds_used = 1
                    elif fresh_iou > 0:
                        # Use fresh code as starting point for refinement
                        initial_iou = fresh_iou
                        best_iou = fresh_iou
                        best_code = fresh_code
                else:
                    print(f"  Fresh gen exec failed: {exec_err}")
            else:
                print(f"  Fresh gen failed: {fresh_err}")

        # Run Claude refinement if not yet passing
        if best_iou < _IOU_THRESHOLD:
            # Use existing code if no fresh code; load from cq_dir
            start_code = best_code
            if start_code is None:
                cq_path = cq_dir / f"{stem}.py"
                if cq_path.exists():
                    start_code = cq_path.read_text(encoding="utf-8")
                else:
                    # No code to refine from — use fresh generation result or skip
                    if best_code is None:
                        print("  SKIP: no initial code to refine")
                        continue
                    start_code = best_code

            refined_code, refined_iou, rounds = _refine_code_with_claude_feedback(
                json_data=json_data,
                initial_code=start_code,
                gt_step_path=gt_step,
                gen_step_path=gen_step,
                initial_iou=initial_iou,
                model=args.model,
                max_rounds=args.max_rounds,
                iou_threshold=_IOU_THRESHOLD,
            )
            rounds_used += rounds
            if refined_iou > best_iou:
                best_iou = refined_iou
                best_code = refined_code

        passed = best_iou >= _IOU_THRESHOLD
        status = f"PASS IoU={best_iou:.4f}" if passed else f"FAIL IoU={best_iou:.4f}"
        print(f"  → {status}  rounds={rounds_used}")

        # Write to refined checkpoint
        record = {
            "stem": stem,
            "initial_iou": part.get("iou", 0),
            "final_iou": best_iou,
            "rounds": rounds_used,
            "passed": passed,
            "model": args.model,
        }
        with refined_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        if passed and best_code:
            revised_cq = cq_dir / f"{stem}_refined.py"
            revised_cq.write_text(best_code, encoding="utf-8")

            complexity = _classify_complexity(json_data)
            entry = {
                "stem": stem,
                "base_stem": stem,
                "raw_step_path": _repo_rel(gt_step),
                "ops_json_path": _repo_rel(json_path),
                "gen_step_path": _repo_rel(gen_step),
                "cq_code_path": _repo_rel(revised_cq),
                "views_raw_dir": None,
                "views_gen_dir": None,
                "complexity_class": complexity,
                "iou": round(best_iou, 6),
                "visual_verdict": "SKIP",
                "visual_reason": f"claude-refined after {rounds_used} rounds",
                "verified": True,
            }
            with args.verified_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=True) + "\n")
            new_verified += 1
            print("  appended to verified_pairs.jsonl")

    # Summary
    total_refined = sum(1 for _ in refined_path.open() if _.strip()) if refined_path.exists() else 0
    total_passed = 0
    if refined_path.exists():
        for line in refined_path.read_text().splitlines():
            if line.strip():
                try:
                    if json.loads(line).get("passed"):
                        total_passed += 1
                except Exception:  # noqa: BLE001
                    pass
    print(f"\nSession: +{new_verified} new verified pairs")
    print(f"Refined checkpoint total: {total_refined} parts, {total_passed} passed")
    print(f"Refined checkpoint: {refined_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
