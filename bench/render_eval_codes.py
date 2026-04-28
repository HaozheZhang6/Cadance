"""Render generated img2cq codes to 4-view composite PNGs.

跑完 eval.py 后, results/img2cq/<model>/codes/<stem>.py 是模型生成的 cadquery.
本脚本对每个 .py 加 OCP HashCode shim, 执行成 STEP, 渲染成 4-view composite,
存到 results/img2cq/<model>/renders/<stem>.png

Resume-safe: 已存在的 renders 跳过.

跑: uv run python bench/render_eval_codes.py --model gpt-4o
    uv run python bench/render_eval_codes.py --models gpt-4o,gpt-5.3-thinking,gpt-5.3-chat-latest
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "data_generation" / "ui"))


# Same shim used by ui/app.py + run_iso_106_codegen — OCP 7.9.3 removed HashCode.
_OCP_SHIM = """\
try:
    from OCP.TopoDS import (TopoDS_Compound, TopoDS_CompSolid, TopoDS_Edge,
                            TopoDS_Face, TopoDS_Shape, TopoDS_Shell,
                            TopoDS_Solid, TopoDS_Vertex, TopoDS_Wire)
    for _cls in (TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex, TopoDS_Wire,
                 TopoDS_Shell, TopoDS_Solid, TopoDS_Compound, TopoDS_CompSolid):
        if not hasattr(_cls, "HashCode"):
            _cls.HashCode = lambda self, ub=2147483647: id(self) % ub
except Exception:
    pass
"""


def _process_model(m: str, workers: int) -> None:
    import tempfile

    code_dir = ROOT / "results" / "img2cq" / m / "codes"
    out_dir = ROOT / "results" / "img2cq" / m / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    codes = sorted(code_dir.glob("*.py"))
    print(f"\n[{m}] {len(codes)} codes from {code_dir.relative_to(ROOT)}", flush=True)

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"render_{m.replace('/', '_')}_"))
    todo = [c for c in codes if not (out_dir / f"{c.stem}.png").exists()]
    n_skip = len(codes) - len(todo)
    n_ok = n_fail = 0
    log_lock = threading.Lock()
    t0 = time.time()

    def _one(idx_cq):
        i, cq = idx_cq
        out_png = out_dir / f"{cq.stem}.png"
        sub = tmp_dir / f"t{threading.get_ident()}"
        sub.mkdir(exist_ok=True)
        t1 = time.time()
        ok, err = render_one(cq, out_png, sub)
        return i, cq, ok, err, time.time() - t1

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
    elapsed = time.time() - t0
    print(
        f"[{m}] done: ok={n_ok} skip={n_skip} fail={n_fail} ({elapsed / 60:.1f}min)",
        flush=True,
    )


def render_one(code_path: Path, out_png: Path, tmp_dir: Path) -> tuple[bool, str]:
    from render import render_cq

    body = code_path.read_text()
    if "TopoDS_Shape" not in body:
        body = _OCP_SHIM + body
    patched = tmp_dir / code_path.name
    patched.write_text(body)
    comp_path, err = render_cq(str(patched), str(tmp_dir))
    patched.unlink(missing_ok=True)
    if comp_path and Path(comp_path).exists():
        out_png.parent.mkdir(parents=True, exist_ok=True)
        Path(comp_path).rename(out_png)
        return True, ""
    return False, (err or "no composite")[:200]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=None, help="single model")
    ap.add_argument(
        "--models",
        default=None,
        help="comma-separated list (overrides --model)",
    )
    ap.add_argument("--workers", type=int, default=1, help="concurrent renders")
    args = ap.parse_args()

    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    elif args.model:
        models = [args.model]
    else:
        sys.exit("provide --model or --models")

    for m in models:
        _process_model(m, args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
