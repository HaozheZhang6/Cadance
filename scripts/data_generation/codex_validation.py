#!/usr/bin/env python
"""Codex golden validation: compare generated CAD against GT STEP.

Two golden standards must both pass for a record to be accepted:
  D1: 3D IoU ≥ IOU_THRESHOLD  (geometric match via OCCT boolean intersection)
  D2: Visual PASS   (4-view PNG comparison via Codex CLI vision)

Skips view rendering for GT when --skip-visual is set (faster runs).

Outputs:
  <out-dir>/validation_report.json   machine-readable results
  <out-dir>/validation_report.md     benchmark comparison report
  <out-dir>/checkpoint.jsonl         per-part results (append-only, resume-safe)

Usage:
  LD_LIBRARY_PATH=/workspace/.local/lib uv run python \\
      scripts/data_generation/codex_validation.py \\
      --limit 1000 --offset 0 --provider auto --skip-visual
  # Resume after interruption:
      ... --resume
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

_LD = "/workspace/.local/lib"
_cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
if _LD not in _cur_ld:
    os.environ["LD_LIBRARY_PATH"] = f"{_LD}:{_cur_ld}".strip(":")

REPO_ROOT = Path(__file__).resolve().parents[2]
STEM_FS = REPO_ROOT / "data/data_generation/generated_data/fusion360"
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
    _build_index,
    _classify_complexity,
    _classify_error_type,
    _compare_views_visual,
    _compute_iou,
    _execute_cadquery_script,
    _generate_code_claude,
    _generate_code_codex,
    _generate_code_openai_with_retry,
    _refine_code_with_feedback,  # noqa: F401 - exported for external use
    _render_views,
    _safe_json_load,
    _step_metrics,
)

# Ordered provider cascade for --cascade mode
CASCADE_PROVIDERS = ["codex", "openai"]

# Default model per provider (used when cascade overrides the CLI --model)
CASCADE_PROVIDER_MODELS = {
    "codex": "gpt-5.3-codex",
    "openai": "gpt-5.2",
}


def _try_codegen(
    json_data: dict,
    provider: str,
    model: str,
    reasoning_effort: str = "high",
    user_prompt: str | None = None,
) -> tuple[str | None, str | None, str]:
    """Attempt codegen with provider fallback. Returns (code, err, used_provider).

    If user_prompt is provided, it overrides the auto-built Fusion360 prompt.
    """
    if provider == "openai":
        code, err = _generate_code_openai_with_retry(
            json_data, model=model, reasoning_effort=reasoning_effort,
            user_prompt=user_prompt,
        )
        return code, err, "openai"

    if provider == "claude":
        code, err = _generate_code_claude(json_data, model=model)
        return code, err, "claude"

    # codex or auto: try primary codex model first
    codex_prompt: str | None = None
    if user_prompt is not None:
        codex_prompt = (
            "Write output.py containing CadQuery Python code.\n"
            f"{user_prompt}\n"
            "- Write ONLY the Python code to output.py, nothing else"
        )
    code, err = _generate_code_codex(
        json_data, model=model, reasoning_effort=reasoning_effort, prompt=codex_prompt
    )
    if code:
        return code, None, "codex"

    if provider == "codex":
        return None, err, "codex"

    # auto: on auth/oauth errors try codex-spark → OpenAI API
    err_type = _classify_error_type(err or "")
    if err_type in ("codex_auth_error", "oauth_error", "timeout", "other"):
        # Fallback 1: codex (alternate model)
        alt = "gpt-5.3-codex" if model != "gpt-5.3-codex" else "gpt-5.3-codex-spark"
        if model not in ("gpt-5.3-codex", "gpt-5.3-codex-spark"):
            alt_code, alt_err = _generate_code_codex(
                json_data, model=alt, reasoning_effort=reasoning_effort,
                prompt=codex_prompt,
            )
            if alt_code:
                return alt_code, None, f"codex-{alt}"

        # Fallback 2: OpenAI API
        code2, err2 = _generate_code_openai_with_retry(
            json_data, model="gpt-5.2", reasoning_effort=reasoning_effort,
            user_prompt=user_prompt,
        )
        if code2:
            return code2, None, "openai"
        return None, f"codex: {err}; openai: {err2}", "openai"

    return None, err, "codex"


def _load_checkpoint(checkpoint_path: Path) -> set[str]:
    """Return set of already-processed stems from checkpoint file."""
    if not checkpoint_path.exists():
        return set()
    stems: set[str] = set()
    with checkpoint_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    stems.add(json.loads(line)["stem"])
                except Exception:  # noqa: BLE001
                    pass
    return stems


def _append_checkpoint(checkpoint_path: Path, result: dict) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=True) + "\n")


def _load_verified_stems(vp_path: Path) -> set[str]:
    """Return set of stems already in verified_pairs.jsonl."""
    if not vp_path.exists():
        return set()
    stems: set[str] = set()
    for line in vp_path.open(encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                stems.add(json.loads(line)["stem"])
            except Exception:  # noqa: BLE001
                pass
    return stems


def _harvest_verified_pair(
    vp_path: Path,
    rec,
    gen_step: Path,
    code_path: Path,
    complexity: str,
    iou: float,
    visual_verdict: str,
    visual_reason: str,
    provider: str,
    run_name: str,
) -> None:
    """Append a passing pair to verified_pairs.jsonl."""
    from scripts.data_generation.build_verified_pairs import REPO_ROOT as _ROOT

    def _rel(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(_ROOT.resolve()))
        except ValueError:
            return str(p)

    raw_base = Path(
        "data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools"
    )
    raw_abs = _ROOT / raw_base
    candidates = sorted(raw_abs.glob(f"{rec.base_stem}*.step"))
    raw_step_rel = (
        f"{raw_base}/{candidates[0].name}" if candidates else _rel(rec.gt_step_path)
    )

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pipeline_run = f"{run_name}_{provider}" if run_name else provider
    record = {
        "stem": rec.base_stem,
        "data_source": "fusion360",
        "gt_step_path": raw_step_rel,
        "gt_json_path": _rel(rec.json_path),
        "gen_step_path": _rel(gen_step),
        "cq_code_path": _rel(code_path),
        "gt_views_norm_dir": "",
        "gen_views_norm_dir": "",
        "complexity_class": complexity,
        "iou": round(iou, 6),
        "visual_verdict": visual_verdict,
        "visual_reason": visual_reason,
        "verified": True,
        "pipeline_run": pipeline_run,
        "timestamp": now,
    }
    vp_path.parent.mkdir(parents=True, exist_ok=True)
    with vp_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    print(f"  ✓ harvested → verified_pairs.jsonl")


def _run_validation(
    limit: int,
    out_dir: Path,
    model: str,
    reasoning_effort: str,
    skip_visual: bool,
    provider: str = "auto",
    offset: int = 0,
    resume: bool = False,
    verified_pairs_path: Path | None = None,
    run_name: str = "",
    cascade: bool = False,
    stems_filter: set[str] | None = None,
) -> list[dict]:
    gen_step_dir = out_dir / "generated_step"
    gen_step_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = out_dir / "checkpoint.jsonl"
    done_stems: set[str] = _load_checkpoint(checkpoint_path) if resume else set()

    verified_stems: set[str] = (
        _load_verified_stems(verified_pairs_path) if verified_pairs_path else set()
    )

    records = _build_index(JSON_DIR, GT_STEP_DIR, limit=limit, offset=offset)
    if stems_filter is not None:
        records = [r for r in records if r.base_stem in stems_filter]
    if not records:
        print("No matched JSON/STEP pairs found.")
        sys.exit(1)

    print(
        f"Found {len(records)} pairs. provider={provider} model={model} "
        f"effort={reasoning_effort} skip_visual={skip_visual} "
        f"offset={offset} resume={resume}"
        + (f" stems_filter={len(stems_filter)}" if stems_filter is not None else "")
        + "\n"
    )
    results: list[dict] = []

    for i, rec in enumerate(records, 1):
        print(f"[{i}/{len(records)}] {rec.base_stem}")

        if rec.base_stem in done_stems:
            print("  SKIP (already in checkpoint)")
            continue

        # GT STEP metrics
        gt_vol, gt_dims, gt_err = _step_metrics(rec.gt_step_path)
        if gt_err:
            print(f"  SKIP gt_step: {gt_err}")
            result = {
                "stem": rec.base_stem,
                "stage": "gt_step",
                "ok": False,
                "error": gt_err,
            }
            results.append(result)
            _append_checkpoint(checkpoint_path, result)
            continue
        print(
            f"  GT vol={gt_vol:.2f}  dims=({gt_dims[0]:.1f},{gt_dims[1]:.1f},{gt_dims[2]:.1f})"
        )

        # Load JSON
        try:
            json_data = _safe_json_load(rec.json_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  SKIP json_load: {exc}")
            result = {
                "stem": rec.base_stem,
                "stage": "json_load",
                "ok": False,
                "error": str(exc),
            }
            results.append(result)
            _append_checkpoint(checkpoint_path, result)
            continue

        complexity = _classify_complexity(json_data)
        print(f"  complexity={complexity}")

        # Provider cascade: try each in sequence until IoU ≥ threshold
        providers_to_try = CASCADE_PROVIDERS if cascade else [provider]
        best_iou = 0.0
        best_code: str | None = None
        best_gen_step: Path | None = None
        best_provider = provider
        best_codegen_sec = 0.0
        last_err = ""
        last_stage = "codegen"
        iou = 0.0
        iou_pass = False
        stem_dir = STEM_FS / rec.base_stem / run_name
        stem_dir.mkdir(parents=True, exist_ok=True)
        code_path = stem_dir / "cq.py"
        gen_step = stem_dir / "gen.step"

        for try_provider in providers_to_try:
            # Use provider-specific model in cascade; use CLI model for the primary provider
            cascade_model = (
                CASCADE_PROVIDER_MODELS.get(try_provider, model)
                if cascade and try_provider != provider
                else model
            )
            t0 = time.time()
            code, err, used_provider = _try_codegen(
                json_data, provider=try_provider, model=cascade_model,
                reasoning_effort=reasoning_effort,
            )
            codegen_sec = round(time.time() - t0, 1)
            if not code:
                print(f"  [{try_provider}] SKIP codegen ({codegen_sec}s): {err}")
                last_err = err or ""
                last_stage = "codegen"
                best_provider = used_provider
                best_codegen_sec = codegen_sec
                continue
            print(f"  [{try_provider}] Codegen OK ({codegen_sec}s, {len(code)} chars)")

            # Save code
            code_path.parent.mkdir(parents=True, exist_ok=True)
            code_path.write_text(code, encoding="utf-8")

            # Execute CQ → STEP
            ran, run_err = _execute_cadquery_script(code, gen_step, timeout_sec=60)
            if not ran:
                print(f"  [{try_provider}] SKIP execute: {run_err}")
                last_err = run_err or ""
                last_stage = "execute"
                best_provider = used_provider
                best_codegen_sec = codegen_sec
                continue
            print(f"  [{try_provider}] Execute OK")

            # Stage D1: 3D IoU
            try_iou, iou_err = _compute_iou(rec.gt_step_path, gen_step)
            if iou_err:
                print(f"  [{try_provider}] SKIP iou: {iou_err}")
                last_err = iou_err
                last_stage = "iou"
                best_provider = used_provider
                best_codegen_sec = codegen_sec
                continue

            print(f"  [{try_provider}] IoU={try_iou:.4f}  D1={'PASS' if try_iou >= IOU_THRESHOLD else 'FAIL'}")
            if try_iou > best_iou:
                best_iou = try_iou
                best_code = code
                best_gen_step = gen_step
                best_provider = used_provider
                best_codegen_sec = codegen_sec
            if try_iou >= IOU_THRESHOLD:
                break  # success — no need to try more providers

        # After cascade: use best result
        used_provider = best_provider
        codegen_sec = best_codegen_sec
        iou = best_iou

        if best_code is None:
            # All providers failed before producing an IoU
            print(f"  SKIP {last_stage}: {last_err}")
            result = {
                "stem": rec.base_stem,
                "stage": last_stage,
                "ok": False,
                "error": last_err,
                "error_type": _classify_error_type(last_err),
                "complexity": complexity,
                "codegen_sec": codegen_sec,
                "provider": used_provider,
            }
            results.append(result)
            _append_checkpoint(checkpoint_path, result)
            continue

        iou_pass = iou >= IOU_THRESHOLD
        print(f"  Best IoU={iou:.4f}  D1={'PASS' if iou_pass else 'FAIL'}  [{used_provider}]")

        # Rename stem dir to verified_ prefix on pass
        if iou_pass:
            verified_dir = STEM_FS / rec.base_stem / f"verified_{run_name}"
            if stem_dir.exists() and not verified_dir.exists():
                stem_dir.rename(verified_dir)
                stem_dir = verified_dir
                code_path = stem_dir / "cq.py"
                gen_step = stem_dir / "gen.step"

        # Stage D2: visual comparison
        visual_verdict = "SKIP"
        visual_reason = ""
        if iou_pass and not skip_visual:
            views_raw_dir = stem_dir / "views_raw"
            views_gen_dir = stem_dir / "views"

            # Render raw views
            rendered_raw, render_err = _render_views(
                rec.gt_step_path, views_raw_dir, max_px=600
            )
            if not rendered_raw:
                visual_verdict = "ERROR"
                visual_reason = f"render_raw: {render_err}"
                print(f"  Visual ERROR (render_raw): {render_err}")
            else:
                # Render gen views
                rendered_gen, render_err = _render_views(
                    gen_step, views_gen_dir, max_px=600
                )
                if not rendered_gen:
                    visual_verdict = "ERROR"
                    visual_reason = f"render_gen: {render_err}"
                    print(f"  Visual ERROR (render_gen): {render_err}")
                else:
                    t1 = time.time()
                    visual_verdict, visual_reason = _compare_views_visual(
                        views_raw_dir, views_gen_dir
                    )
                    visual_sec = round(time.time() - t1, 1)
                    print(
                        f"  D2 visual={visual_verdict} ({visual_sec}s)"
                        + (f" reason={visual_reason[:60]}" if visual_reason else "")
                    )
        elif not iou_pass:
            visual_verdict = "SKIP"
            visual_reason = f"IoU={iou:.3f} < {IOU_THRESHOLD} — visual skipped"

        # When --skip-visual: D1 alone is the acceptance criterion.
        verified = iou_pass and (skip_visual or visual_verdict == "PASS")
        status = "PASS" if verified else ("FAIL" if iou_pass else "FAIL_IoU")
        print(f"  → {status}  IoU={iou:.4f}  visual={visual_verdict}  [{used_provider}]")

        result = {
            "stem": rec.base_stem,
            "stage": "done",
            "ok": verified,
            "complexity": complexity,
            "codegen_sec": codegen_sec,
            "gt_vol": round(gt_vol, 4),
            "iou": round(iou, 6),
            "iou_pass": iou_pass,
            "visual_verdict": visual_verdict,
            "visual_reason": visual_reason,
            "provider": used_provider,
        }
        results.append(result)
        _append_checkpoint(checkpoint_path, result)

        # Auto-harvest into verified_pairs.jsonl
        if verified and verified_pairs_path and rec.base_stem not in verified_stems:
            _harvest_verified_pair(
                vp_path=verified_pairs_path,
                rec=rec,
                gen_step=gen_step,
                code_path=code_path,
                complexity=complexity,
                iou=iou,
                visual_verdict=visual_verdict,
                visual_reason=visual_reason,
                provider=used_provider,
                run_name=run_name,
            )
            verified_stems.add(rec.base_stem)

    return results


def _write_md_report(
    results: list[dict],
    out_path: Path,
    model: str,
    reasoning_effort: str,
    skip_visual: bool,
) -> None:
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(results)
    done = [r for r in results if r.get("stage") == "done"]
    passed = sum(1 for r in done if r.get("ok"))
    iou_passed = sum(1 for r in done if r.get("iou_pass"))
    visual_passed = sum(1 for r in done if r.get("visual_verdict") == "PASS")
    executed = len(done) + sum(1 for r in results if r.get("stage") == "iou")

    stage_counts: dict[str, int] = {}
    for r in results:
        if not r.get("ok"):
            s = r.get("stage", "?")
            stage_counts[s] = stage_counts.get(s, 0) + 1

    avg_iou = sum(r["iou"] for r in done) / len(done) if done else None
    avg_codegen = (
        sum(r.get("codegen_sec", 0) for r in results if r.get("codegen_sec"))
        / sum(1 for r in results if r.get("codegen_sec"))
        if any(r.get("codegen_sec") for r in results)
        else None
    )

    lines: list[str] = []
    lines.append("# Codex CLI vs GT STEP — Benchmark Report\n")
    lines.append(f"**Date:** {date_str}  ")
    lines.append(f"**Model:** `{model}` (reasoning_effort=`{reasoning_effort}`)  ")
    lines.append("**Corpus:** Fusion360 Gallery r1.0.1  ")
    lines.append(
        f"**Validation:** D1 IoU ≥ {IOU_THRESHOLD}"
        + (" + D2 Visual" if not skip_visual else " only (--skip-visual)")
        + "  \n"
    )

    lines.append("## Summary\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Parts tested | {total} |")
    lines.append(f"| CQ executed | {executed} |")
    pct = lambda n: f"{n / total * 100:.0f}%" if total else "—"
    lines.append(
        f"| D1 IoU ≥ {IOU_THRESHOLD} | {iou_passed} ({pct(iou_passed)}) |"
    )
    if not skip_visual:
        lines.append(
            f"| D2 Visual PASS | {visual_passed} ({pct(visual_passed)}) |"
        )
    lines.append(
        f"| **VERIFIED (D1 AND D2)** | **{passed} ({pct(passed)})** |"
    )
    if avg_iou is not None:
        lines.append(f"| Avg IoU (executed) | {avg_iou:.4f} |")
    if avg_codegen is not None:
        lines.append(f"| Avg codegen time | {avg_codegen:.0f}s |")
    lines.append("")

    if stage_counts:
        lines.append("## Failure Breakdown by Stage\n")
        lines.append("| Stage | Count |")
        lines.append("|-------|-------|")
        for stage, cnt in sorted(stage_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {stage} | {cnt} |")
        lines.append("")

    lines.append("## Per-Part Benchmark Comparison\n")
    if skip_visual:
        lines.append(
            "| Stem | Complexity | GT Vol (mm³) | IoU | D1 | Codegen (s) | Result |"
        )
        lines.append(
            "|------|-----------|-------------|-----|----|----|-------------|--------|"
        )
    else:
        lines.append(
            "| Stem | Complexity | GT Vol (mm³) | IoU | D1 | D2 Visual | Codegen (s) | Result |"
        )
        lines.append(
            "|------|-----------|-------------|-----|----|----|-----------|-------------|--------|"
        )

    for r in results:
        stem = r["stem"]
        comp = r.get("complexity", "—")
        codegen_s = f"{r['codegen_sec']:.0f}" if r.get("codegen_sec") else "—"

        if r.get("stage") == "done":
            gt_v = f"{r['gt_vol']:.1f}"
            iou_v = f"{r['iou']:.4f}"
            d1 = "✅" if r.get("iou_pass") else "❌"
            d2 = r.get("visual_verdict", "SKIP")
            d2_icon = (
                "✅" if d2 == "PASS" else ("⚠️" if d2 in ("SKIP", "ERROR") else "❌")
            )
            result = "✅ PASS" if r.get("ok") else "❌ FAIL"
            if skip_visual:
                lines.append(
                    f"| `{stem}` | {comp} | {gt_v} | {iou_v} | {d1} | {codegen_s} | {result} |"
                )
            else:
                lines.append(
                    f"| `{stem}` | {comp} | {gt_v} | {iou_v} | {d1} | {d2_icon} {d2} | {codegen_s} | {result} |"
                )
        else:
            gt_v = iou_v = d1 = d2 = "—"
            result = f"⚠️ SKIP@{r.get('stage','?')}"
            if skip_visual:
                lines.append(
                    f"| `{stem}` | {comp} | {gt_v} | {iou_v} | {d1} | {codegen_s} | {result} |"
                )
            else:
                lines.append(
                    f"| `{stem}` | {comp} | {gt_v} | {iou_v} | {d1} | {d2} | {codegen_s} | {result} |"
                )

    lines.append("")

    # Visual failure details
    visual_fails = [
        r for r in done if r.get("visual_verdict") == "FAIL" and r.get("visual_reason")
    ]
    if visual_fails:
        lines.append("## Visual Failure Details\n")
        for r in visual_fails:
            lines.append(f"**`{r['stem']}`**: {r['visual_reason']}\n")
        lines.append("")

    lines.append("## Notes\n")
    lines.append(
        "- Fusion360 JSON coordinates in **cm**; multiplied ×10 for CadQuery (mm)."
    )
    lines.append(
        f"- D1 threshold: IoU ≥ {IOU_THRESHOLD} (OCCT boolean intersection/union)."
    )
    if not skip_visual:
        lines.append(
            "- D2: 4-view PNGs (front/right/top/iso) of both STEPs compared via Codex CLI vision."
        )
    lines.append(
        "- Auth: ChatGPT OAuth device flow, token at `/workspace/.codex/auth.json`."
    )
    lines.append(
        "- Pipeline: `_build_index` → GT metrics → codegen → execute → IoU"
        + (" → visual" if not skip_visual else "")
        + "."
    )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=1000, help="Parts to test (0=all)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N parts")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "data/codex_validation",
    )
    parser.add_argument("--run-name", default="", help="Subdirectory name for this run")
    parser.add_argument("--model", default="gpt-5.3-codex")
    parser.add_argument("--reasoning-effort", default="high", dest="reasoning_effort")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "codex", "openai", "claude"],
        help="auto=codex→openai fallback; codex=codex only; openai=openai only; claude=claude only",
    )
    parser.add_argument(
        "--skip-visual",
        action="store_true",
        help="Skip D2 visual comparison (IoU-only, faster)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint.jsonl (skip already-processed stems)",
    )
    parser.add_argument(
        "--verified-pairs",
        type=Path,
        default=REPO_ROOT / "data/data_generation/verified/verified_pairs.jsonl",
        dest="verified_pairs",
        help="Auto-harvest passing pairs into this file (default: data/data_generation/verified/verified_pairs.jsonl)",
    )
    parser.add_argument(
        "--no-harvest",
        action="store_true",
        dest="no_harvest",
        help="Disable auto-harvest of passing pairs into verified_pairs.jsonl",
    )
    parser.add_argument(
        "--cascade",
        action="store_true",
        help=f"Try providers in sequence {CASCADE_PROVIDERS} per mesh until IoU≥{IOU_THRESHOLD}",
    )
    parser.add_argument(
        "--stems-file",
        type=Path,
        default=None,
        dest="stems_file",
        help="Text file with one stem per line; only process those stems",
    )
    args = parser.parse_args()

    out_dir = args.out_dir
    if args.run_name:
        out_dir = out_dir / args.run_name

    verified_pairs_path = None if args.no_harvest else args.verified_pairs

    stems_filter: set[str] | None = None
    if args.stems_file:
        stems_filter = set(
            line.strip() for line in args.stems_file.read_text().splitlines() if line.strip()
        )
        print(f"Loaded {len(stems_filter)} stems from {args.stems_file}")

    results = _run_validation(
        limit=args.limit,
        out_dir=out_dir,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        skip_visual=args.skip_visual,
        provider=args.provider,
        offset=args.offset,
        resume=args.resume,
        verified_pairs_path=verified_pairs_path,
        run_name=args.run_name,
        cascade=args.cascade,
        stems_filter=stems_filter,
    )

    total = len(results)
    passed = sum(1 for r in results if r.get("ok") and r.get("stage") == "done")
    iou_passed = sum(
        1 for r in results if r.get("stage") == "done" and r.get("iou_pass")
    )
    executed = sum(1 for r in results if r.get("stage") == "done")

    print(f"\n{'='*60}")
    print(
        f"RESULTS: {passed}/{total} VERIFIED  |  {iou_passed}/{executed} IoU≥{IOU_THRESHOLD}"
    )
    print(f"{'='*60}")
    for r in results:
        if r.get("stage") == "done":
            iou_str = f"IoU={r.get('iou', 0):.4f}"
            vis_str = f"vis={r.get('visual_verdict', 'SKIP')}"
            s = "PASS" if r.get("ok") else f"FAIL  {iou_str}  {vis_str}"
        else:
            s = f"SKIP@{r.get('stage','?')}"
        print(f"  {r['stem']:42s}  {s}")

    # JSON report
    report = {
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "provider": args.provider,
        "offset": args.offset,
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "iou_threshold": IOU_THRESHOLD,
        "skip_visual": args.skip_visual,
        "total": total,
        "passed": passed,
        "iou_passed": iou_passed,
        "executed": executed,
        "results": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "validation_report.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown benchmark report
    md_path = out_dir / "validation_report.md"
    _write_md_report(
        results, md_path, args.model, args.reasoning_effort, args.skip_visual
    )

    print(f"\nJSON report : {json_path}")
    print(f"MD report   : {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
