"""Run the CAD edit benchmark with VISION — model sees image + code + instruction.

Same task as run_edit.py but each call gets a 2x2 composite render of the
original part alongside the code + instruction. The image is rendered on the
fly from the `orig_step` bytes in the HF dataset.

Usage (zero-setup, HF):
    python -m bench.edit_gen.run_edit_vlm --model gpt-4o --n 20

Usage (local bench dir):
    python -m bench.edit_gen.run_edit_vlm --model gpt-4o \
        --bench-dir data/data_generation/bench_edit
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bench.edit_gen.run_edit import exec_cq  # noqa: E402

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
    bench_dir: Path | None,
    hf_repo: str | None,
    hf_split: str,
):
    if hf_repo:
        from bench.dataloader import load_hf

        rows = load_hf(hf_repo, hf_split)
        return list(rows), "hf"

    assert bench_dir is not None
    pairs_path = bench_dir / "pairs.jsonl"
    records = [json.loads(ln) for ln in pairs_path.read_text().splitlines() if ln]
    for r in records:
        r["orig_code"] = (bench_dir / r["original_code_path"]).read_text()
        r["orig_step"] = (bench_dir / r["original_step_path"]).read_bytes()
    return records, "local"


def run(
    bench_dir: Path | None,
    model: str,
    n: int | None,
    seed: int,
    skip_existing: bool,
    hf_repo: str | None = None,
    hf_split: str = "test",
    out_dir: Path | None = None,
) -> dict:
    from bench.models import call_edit_vlm

    records, _src = _load_records(bench_dir, hf_repo, hf_split)

    import random as _random

    _random.Random(seed).shuffle(records)
    if n:
        records = records[:n]

    run_root = out_dir or (
        bench_dir / "runs_vlm" if bench_dir else Path("bench_edit_vlm_runs")
    )
    run_dir = run_root / model.replace(":", "_").replace("/", "_")
    gen_code_dir = run_dir / "gen_code"
    gen_step_dir = run_dir / "gen_step"
    gen_code_dir.mkdir(parents=True, exist_ok=True)
    gen_step_dir.mkdir(parents=True, exist_ok=True)
    results_path = run_dir / "results.jsonl"

    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY1")
    if not key:
        raise RuntimeError("set OPENAI_API_KEY or OPENAI_API_KEY1")

    fh = results_path.open("w")
    n_total = len(records)
    n_api_ok = n_exec_ok = 0
    t0 = time.time()

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)

        for i, rec in enumerate(records):
            rid = rec["record_id"]
            orig_code = rec["orig_code"]
            instruction = rec["instruction"]
            orig_step_bytes = rec["orig_step"]

            gen_code_path = gen_code_dir / f"{rid}.py"
            gen_step_path = gen_step_dir / f"{rid}.step"

            if skip_existing and gen_code_path.exists() and gen_step_path.exists():
                n_api_ok += 1
                n_exec_ok += 1
                fh.write(
                    json.dumps(
                        {
                            "record_id": rid,
                            "api_ok": True,
                            "exec_ok": True,
                            "skipped": True,
                        }
                    )
                    + "\n"
                )
                continue

            t_render = time.time()
            try:
                img = _render_composite(orig_step_bytes, tmpdir, rid)
                render_err = None
            except Exception as e:
                img, render_err = None, str(e)[:200]
            render_dt = time.time() - t_render

            if img is None:
                fh.write(
                    json.dumps(
                        {
                            "record_id": rid,
                            "api_ok": False,
                            "render_err": render_err,
                            "exec_ok": False,
                        }
                    )
                    + "\n"
                )
                fh.flush()
                print(
                    f"[{i+1:3d}/{n_total}] {rid:60s} RENDER_FAIL {render_err[:40]}",
                    flush=True,
                )
                continue

            t_api = time.time()
            code, api_err = call_edit_vlm(model, orig_code, instruction, img, key)
            api_dt = time.time() - t_api
            api_ok = code is not None
            exec_ok = False
            exec_err = None

            if api_ok:
                gen_code_path.write_text(code)
                n_api_ok += 1
                exec_ok, exec_err = exec_cq(code, gen_step_path)
                if exec_ok:
                    n_exec_ok += 1

            fh.write(
                json.dumps(
                    {
                        "record_id": rid,
                        "family": rec["family"],
                        "difficulty": rec["difficulty"],
                        "level": rec["level"],
                        "axis": rec["axis"],
                        "pct_delta": rec["pct_delta"],
                        "api_ok": api_ok,
                        "api_err": api_err,
                        "api_latency_s": round(api_dt, 3),
                        "render_latency_s": round(render_dt, 3),
                        "exec_ok": exec_ok,
                        "exec_err": exec_err,
                    }
                )
                + "\n"
            )
            fh.flush()

            print(
                f"[{i+1:3d}/{n_total}] {rid:60s} api={'Y' if api_ok else 'N'}"
                f" exec={'Y' if exec_ok else 'N'} render={render_dt:4.1f}s api={api_dt:4.1f}s",
                flush=True,
            )

    fh.close()
    elapsed = time.time() - t0

    summary = {
        "model": model,
        "mode": "vlm",
        "n_total": n_total,
        "api_ok": n_api_ok,
        "exec_ok": n_exec_ok,
        "api_rate": round(n_api_ok / max(n_total, 1), 4),
        "exec_rate": round(n_exec_ok / max(n_total, 1), 4),
        "elapsed_s": round(elapsed, 1),
        "seed": seed,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{json.dumps(summary, indent=2)}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--hf-repo",
        type=str,
        default="BenchCAD/cad_bench_edit",
        help="HF dataset repo. Empty => use --bench-dir.",
    )
    ap.add_argument("--split", type=str, default="test")
    ap.add_argument(
        "--bench-dir",
        type=str,
        default="",
        help="Local bench dir with pairs.jsonl + codes/ + steps/",
    )
    ap.add_argument("--model", type=str, default="gpt-4o")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()
    bench_dir = Path(args.bench_dir) if args.bench_dir else None
    hf_repo = args.hf_repo if not bench_dir else None
    out_dir = Path(args.out) if args.out else None
    run(
        bench_dir,
        args.model,
        args.n,
        args.seed,
        args.skip_existing,
        hf_repo=hf_repo,
        hf_split=args.split,
        out_dir=out_dir,
    )


if __name__ == "__main__":
    main()
