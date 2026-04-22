"""Filter for HF upload: drop non-accepted / missing-files / exec-fail stems.

Usage (from upload scripts):
    from ._upload_filter import filter_rows, accepted_stems
    stems_ok = accepted_stems(run_name)
    rows, drop_stats = filter_rows(meta_files, stems_ok, revalidate_code=True)
"""

from __future__ import annotations

import signal
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SYNTH_CSV = ROOT / "data" / "data_generation" / "synth_parts.csv"
# Canonical blocklist: stems dropped by the upload filter, readable by UI.
BLOCKLIST_CSV = ROOT / "data" / "data_generation" / "upload_blocklist.csv"

REQUIRED_FILES = (
    "code.py",
    "gen.step",
    "meta.json",
    "render_0.png",
    "render_1.png",
    "render_2.png",
    "render_3.png",
    "views/composite.png",
)


def accepted_stems(run_name: str | None = None) -> set[str]:
    """Set of stems with status=='accepted' (optionally scoped to one pipeline_run)."""
    df = pd.read_csv(SYNTH_CSV)
    df = df[df["status"] == "accepted"]
    if run_name:
        df = df[df["pipeline_run"] == run_name]
    return set(df["stem"].dropna().tolist())


def check_files(run_dir: Path) -> str | None:
    """Return None if all required files present, else missing-file reason."""
    for rel in REQUIRED_FILES:
        if not (run_dir / rel).exists():
            return f"missing:{rel}"
    return None


_WORKER_READY = False


def _worker_init():
    """Per-worker one-time setup: patch HashCode for OCP 7.7.2 + cadquery 2.3.0."""
    global _WORKER_READY
    if _WORKER_READY:
        return
    from OCP.TopoDS import (
        TopoDS_Compound,
        TopoDS_CompSolid,
        TopoDS_Edge,
        TopoDS_Face,
        TopoDS_Shape,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Vertex,
        TopoDS_Wire,
    )

    for _c in [
        TopoDS_Shape,
        TopoDS_Face,
        TopoDS_Edge,
        TopoDS_Vertex,
        TopoDS_Wire,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Compound,
        TopoDS_CompSolid,
    ]:
        if not hasattr(_c, "HashCode"):
            _c.HashCode = lambda self, ub=2147483647: id(self) % ub
    import cadquery  # noqa: F401 — warm import cache

    _WORKER_READY = True


class _Timeout(Exception):
    pass


def _on_alarm(_sig, _frm):
    raise _Timeout()


_EXEC_TIMEOUT_SEC = 45


def _exec_code(args) -> tuple[str, str | None]:
    """Worker: in-process exec of code.py with SIGALRM timeout."""
    stem, code_path = args
    _worker_init()
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(_EXEC_TIMEOUT_SEC)
    try:
        code_src = Path(code_path).read_text()
        g: dict = {"__name__": "__main__", "show_object": lambda *a, **k: None}
        exec(compile(code_src, str(code_path), "exec"), g)
        r = g.get("result")
        if r is None:
            return stem, "exec_fail:no_result"
        try:
            v = r.val().Volume()
        except Exception as e:
            return stem, f"exec_fail:vol:{type(e).__name__}"
        if v <= 0:
            return stem, "exec_fail:zero_volume"
        return stem, None
    except _Timeout:
        return stem, "exec_timeout"
    except Exception as e:
        return stem, f"exec_fail:{type(e).__name__}"
    finally:
        signal.alarm(0)


def revalidate_exec(pairs: list[tuple[str, Path]], workers: int = 8) -> dict[str, str]:
    """Return {stem: reason} for stems whose code.py fails to exec under current env."""
    bad: dict[str, str] = {}
    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as pool:
        futs = {pool.submit(_exec_code, p): p[0] for p in pairs}
        done = 0
        n = len(pairs)
        for fut in as_completed(futs):
            try:
                stem, reason = fut.result(timeout=_EXEC_TIMEOUT_SEC * 4)
            except Exception as e:
                stem = futs[fut]
                reason = f"worker_err:{type(e).__name__}"
            if reason:
                bad[stem] = reason
            done += 1
            if done % 500 == 0 or done == n:
                print(f"    exec-check [{done}/{n}] bad so far: {len(bad)}", flush=True)
    return bad


def _write_blocklist(pipeline_run: str, dropped_detail: list[tuple[str, str]]) -> None:
    """Upsert blocklist rows for `pipeline_run`. Other runs' rows preserved."""
    BLOCKLIST_CSV.parent.mkdir(parents=True, exist_ok=True)
    if BLOCKLIST_CSV.exists():
        existing = pd.read_csv(BLOCKLIST_CSV)
        existing = existing[existing["pipeline_run"] != pipeline_run]
    else:
        existing = pd.DataFrame(columns=["stem", "reason", "pipeline_run"])
    fresh = pd.DataFrame(
        [(s, r, pipeline_run) for s, r in dropped_detail],
        columns=["stem", "reason", "pipeline_run"],
    )
    combined = pd.concat([existing, fresh], ignore_index=True)
    combined.to_csv(BLOCKLIST_CSV, index=False)
    print(
        f"  blocklist → {BLOCKLIST_CSV.relative_to(ROOT)} "
        f"({len(fresh)} new rows for {pipeline_run}, {len(combined)} total)"
    )


def filter_rows(
    meta_files: list[Path],
    accepted: set[str],
    revalidate_code: bool = True,
    workers: int = 8,
    dropped_log: Path | None = None,
    pipeline_run: str | None = None,
) -> tuple[list[Path], dict[str, int]]:
    """Apply 3-layer filter. Returns (kept_meta_files, drop_counts_by_reason).

    If dropped_log is given, writes CSV of (stem, reason) for every dropped stem.
    If pipeline_run is given, upserts the canonical `upload_blocklist.csv`.
    """
    drops: dict[str, int] = {}
    dropped_detail: list[tuple[str, str]] = []

    kept_after_csv: list[Path] = []
    for mf in meta_files:
        stem = mf.parent.parent.name  # .../fusion360/<stem>/verified_<run>/meta.json
        if stem not in accepted:
            drops["status_not_accepted"] = drops.get("status_not_accepted", 0) + 1
            dropped_detail.append((stem, "status_not_accepted"))
            continue
        kept_after_csv.append(mf)

    kept_after_files: list[Path] = []
    for mf in kept_after_csv:
        reason = check_files(mf.parent)
        if reason:
            drops[reason] = drops.get(reason, 0) + 1
            dropped_detail.append((mf.parent.parent.name, reason))
            continue
        kept_after_files.append(mf)

    if revalidate_code:
        pairs = [
            (mf.parent.parent.name, mf.parent / "code.py") for mf in kept_after_files
        ]
        print(
            f"  revalidating code.py exec on {len(pairs)} samples (parallel × {workers}) ...",
            flush=True,
        )
        bad = revalidate_exec(pairs, workers=workers)
        for stem, reason in bad.items():
            bucket = reason.split(":")[0] if ":" in reason else reason
            drops[bucket] = drops.get(bucket, 0) + 1
            dropped_detail.append((stem, reason))
        kept_final = [mf for mf in kept_after_files if mf.parent.parent.name not in bad]
    else:
        kept_final = kept_after_files

    if dropped_log and dropped_detail:
        dropped_log.parent.mkdir(parents=True, exist_ok=True)
        with open(dropped_log, "w") as f:
            f.write("stem,reason\n")
            for stem, reason in dropped_detail:
                f.write(f"{stem},{reason}\n")
        print(f"  dropped log → {dropped_log} ({len(dropped_detail)} rows)")

    if pipeline_run:
        _write_blocklist(pipeline_run, dropped_detail)

    return kept_final, drops
