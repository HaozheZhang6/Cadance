"""Edit-img bench — vision edit (model sees orig CQ code + 4-view img + NL instruction).

Same task as run_edit_code.py but each call gets a 2x2 composite render of the
original part. The image is rendered on the fly from the `orig_step` bytes in
the HF dataset (or from the local STEP file).

Results land in `results/edit_img/<model>/`, dedup by record_id across runs.

Usage (zero-setup, HF):
    python -m bench.edit_gen.run_edit_img --model gpt-4o --limit 20 --seed 42

Usage (local bench dir):
    python -m bench.edit_gen.run_edit_img --model gpt-4o \
        --bench-dir data/data_generation/bench_edit
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bench.edit_gen.run_edit_code import exec_cq  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass


def _render_composite(step_bytes: bytes, tmpdir: Path, name: str):
    from PIL import Image

    from scripts.data_generation.render_normalized_views import render_step_normalized

    step_path = tmpdir / f"{name}.step"
    step_path.write_bytes(step_bytes)
    out_dir = tmpdir / f"{name}_views"
    paths = render_step_normalized(str(step_path), str(out_dir))
    return Image.open(paths["composite"]).copy()


def _load_records(
    bench_dir: Path | None, hf_repo: str | None, hf_split: str
) -> list[dict]:
    if hf_repo:
        from bench.dataloader import load_hf

        rows = load_hf(hf_repo, hf_split)
        return list(rows)

    assert bench_dir is not None
    pairs_path = bench_dir / "pairs.jsonl"
    records = [json.loads(ln) for ln in pairs_path.read_text().splitlines() if ln]
    for r in records:
        r["orig_code"] = (bench_dir / r["original_code_path"]).read_text()
        r["orig_step"] = (bench_dir / r["original_step_path"]).read_bytes()
    return records


def run(
    bench_dir: Path | None,
    model: str,
    n: int,
    seed: int,
    hf_repo: str | None,
    hf_split: str,
) -> dict:
    from bench.models import call_edit_vlm
    from bench.results import ResultsDir
    from bench.sampling import sample_rows

    records = _load_records(bench_dir, hf_repo, hf_split)
    sampled = sample_rows(records, n, seed, stratify_key="family", id_key="record_id")

    rd = ResultsDir(task="edit_img", model=model)
    done = rd.done_keys("record_id")
    todo = [r for r in sampled if r["record_id"] not in done]
    rd.log_run(
        {
            "seed": seed,
            "limit": n,
            "split": hf_split,
            "model": model,
            "hf_repo": hf_repo,
        },
        sampled,
        id_key="record_id",
    )

    print(f"Sampled {len(sampled)} (seed={seed})  done={len(done)}  todo={len(todo)}")
    print(f"Results dir: {rd.root}")

    n_total = len(todo)
    n_api_ok = n_exec_ok = 0
    t0 = time.time()

    with rd, tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        for i, rec in enumerate(todo):
            rid = rec["record_id"]
            orig_code = rec["orig_code"]
            instruction = rec["instruction"]
            orig_step_bytes = rec["orig_step"]

            t_render = time.time()
            try:
                img = _render_composite(orig_step_bytes, tmpdir, rid)
                render_err = None
            except Exception as e:
                img, render_err = None, str(e)[:200]
            render_dt = time.time() - t_render

            if img is None:
                rd.append(
                    {
                        "record_id": rid,
                        "model": model,
                        "api_ok": False,
                        "render_err": render_err,
                        "exec_ok": False,
                    }
                )
                print(
                    f"[{i + 1:3d}/{n_total}] {rid:60s} RENDER_FAIL {render_err[:40]}",
                    flush=True,
                )
                continue

            t_api = time.time()
            code, api_err = call_edit_vlm(model, orig_code, instruction, img)
            api_dt = time.time() - t_api
            api_ok = code is not None
            exec_ok = False
            exec_err = None

            if api_ok:
                rd.save_code(rid, code)
                n_api_ok += 1
                rd.steps.mkdir(parents=True, exist_ok=True)
                step_path = rd.steps / f"{rid}.step"
                exec_ok, exec_err = exec_cq(code, step_path)
                if exec_ok:
                    n_exec_ok += 1

            rd.append(
                {
                    "record_id": rid,
                    "family": rec["family"],
                    "difficulty": rec["difficulty"],
                    "level": rec["level"],
                    "axis": rec["axis"],
                    "pct_delta": rec["pct_delta"],
                    "model": model,
                    "api_ok": api_ok,
                    "api_err": api_err,
                    "api_latency_s": round(api_dt, 3),
                    "render_latency_s": round(render_dt, 3),
                    "exec_ok": exec_ok,
                    "exec_err": exec_err,
                }
            )
            print(
                f"[{i + 1:3d}/{n_total}] {rid:60s} api={'Y' if api_ok else 'N'}"
                f" exec={'Y' if exec_ok else 'N'} render={render_dt:4.1f}s api={api_dt:4.1f}s",
                flush=True,
            )

    elapsed = time.time() - t0
    summary = {
        "model": model,
        "mode": "img",
        "n_total": n_total,
        "api_ok": n_api_ok,
        "exec_ok": n_exec_ok,
        "api_rate": round(n_api_ok / max(n_total, 1), 4),
        "exec_rate": round(n_exec_ok / max(n_total, 1), 4),
        "elapsed_s": round(elapsed, 1),
        "seed": seed,
    }
    (rd.root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{json.dumps(summary, indent=2)}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument(
        "--hf-repo",
        default="BenchCAD/cad_bench_edit",
        help="HF repo (empty => use --bench-dir)",
    )
    ap.add_argument("--split", default="test")
    ap.add_argument(
        "--bench-dir", default="", help="Local bench dir (overrides --hf-repo)"
    )
    ap.add_argument("--limit", type=int, default=0, help="0=all; >200 stratified")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    bench_dir = Path(args.bench_dir) if args.bench_dir else None
    hf_repo = args.hf_repo if not bench_dir else None
    run(
        bench_dir,
        args.model,
        args.limit,
        args.seed,
        hf_repo=hf_repo,
        hf_split=args.split,
    )


if __name__ == "__main__":
    main()
