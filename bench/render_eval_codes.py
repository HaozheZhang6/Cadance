"""Render generated img2cq codes to 4-view composite PNGs.

跑完 eval.py 后, results/img2cq/<model>/codes/<stem>.py 是模型生成的 cadquery.
本脚本对每个 .py 起一个 subprocess (`bench/_render_subproc.py`), 加 OCP shim,
执行成 STEP, 渲染成 4-view composite, 存到 results/img2cq/<model>/renders/<stem>.png

为啥 subprocess 而不是 ProcessPoolExecutor:
- macOS VTK 复杂几何 (enclosure / gusseted_bracket 等) 偶尔卡 4+ min
- subprocess.run(timeout=N) SIGKILL 干净,丢失最多 1 个 render 不污染 worker
- ThreadPool wait subprocess = 4 并发 = 4× 速度,无 Cocoa 主线程冲突

Resume-safe: 已存在的 renders 跳过.

跑: uv run python bench/render_eval_codes.py \\
        --models gpt-4o,gpt-5.3-chat-latest,gpt-5.3-thinking \\
        --stems-file <txt> --workers 4 --timeout 60
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBPROC = ROOT / "bench" / "_render_subproc.py"


def _render_one(
    cq_path: Path, out_png: Path, tmp_dir: Path, timeout: int
) -> tuple[bool, str, float]:
    sub = tmp_dir / cq_path.stem
    sub.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(SUBPROC), str(cq_path), str(out_png), str(sub)]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timeout >{timeout}s", float(timeout)
    dt = time.time() - t0
    if r.returncode == 0 and out_png.exists():
        return True, "", dt
    err = (r.stderr.decode(errors="replace") if r.stderr else "no stderr")[:200]
    return False, err, dt


def _process_model(m: str, workers: int, timeout: int, wanted: set[str] | None) -> None:
    code_dir = ROOT / "results" / "img2cq" / m / "codes"
    out_dir = ROOT / "results" / "img2cq" / m / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    codes = sorted(code_dir.glob("*.py"))
    if wanted is not None:
        codes = [c for c in codes if c.stem in wanted]
    todo = [c for c in codes if not (out_dir / f"{c.stem}.png").exists()]
    n_skip = len(codes) - len(todo)
    print(
        f"\n[{m}] {len(codes)} codes ({n_skip} skip already-rendered, {len(todo)} todo)",
        flush=True,
    )
    if not todo:
        return

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"render_{m.replace('/', '_')}_"))
    n_ok = n_fail = 0
    log_lock = threading.Lock()
    t0 = time.time()

    def _one(idx_cq):
        i, cq = idx_cq
        out_png = out_dir / f"{cq.stem}.png"
        ok, err, dt = _render_one(cq, out_png, tmp_dir, timeout)
        return i, cq, ok, err, dt

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(_one, (i, cq)) for i, cq in enumerate(todo)]
        for done_i, fut in enumerate(as_completed(futs)):
            _i, cq, ok, err, dt = fut.result()
            with log_lock:
                if ok:
                    n_ok += 1
                    print(
                        f"  [{done_i + 1}/{len(todo)}] {cq.stem} OK {dt:.1f}s",
                        flush=True,
                    )
                else:
                    n_fail += 1
                    print(
                        f"  [{done_i + 1}/{len(todo)}] {cq.stem} "
                        f"FAIL {dt:.1f}s: {err[:120]}",
                        flush=True,
                    )
    print(
        f"[{m}] done: ok={n_ok} skip={n_skip} fail={n_fail} "
        f"({(time.time() - t0) / 60:.1f}min)",
        flush=True,
    )


def _load_stems(p: Path) -> set[str]:
    import json

    out: set[str] = set()
    for line in p.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("{"):
            try:
                s = json.loads(s).get("stem", "")
            except Exception:
                s = ""
        if s:
            out.add(s)
    return out


def _load_stems_from_parquet() -> set[str] | None:
    """Auto-detect cad_bench_200 parquet in hf_cache, return its 200 stems."""
    glob = (
        "data/hf_cache/hub/datasets--BenchCAD--cad_bench_200/snapshots/*/data/*.parquet"
    )
    snaps = sorted(ROOT.glob(glob))
    if not snaps:
        return None
    import pyarrow.parquet as pq

    t = pq.read_table(snaps[-1], columns=["stem"])
    return set(t["stem"].to_pylist())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=None)
    ap.add_argument("--models", default=None, help="comma-separated list")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=60, help="per-render seconds")
    ap.add_argument(
        "--stems-file",
        default=None,
        help="txt or jsonl with stems to render. If omitted, "
        "auto-detect cad_bench_200 from hf_cache; falls back to all stems.",
    )
    args = ap.parse_args()

    if args.models:
        models = [s.strip() for s in args.models.split(",") if s.strip()]
    elif args.model:
        models = [args.model]
    else:
        sys.exit("provide --model or --models")

    wanted: set[str] | None
    if args.stems_file:
        wanted = _load_stems(Path(args.stems_file))
        print(f"[stems] {len(wanted)} from {args.stems_file}", flush=True)
    else:
        wanted = _load_stems_from_parquet()
        if wanted:
            print(f"[stems] {len(wanted)} from cad_bench_200 (auto)", flush=True)
        else:
            print("[stems] no filter (rendering ALL codes per model)", flush=True)

    for m in models:
        _process_model(m, args.workers, args.timeout, wanted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
