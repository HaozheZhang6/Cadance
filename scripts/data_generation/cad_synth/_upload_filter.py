"""Filter for HF upload: drop non-accepted / missing-files / exec-fail stems.

Usage (from upload scripts):
    from ._upload_filter import filter_rows, accepted_stems
    stems_ok = accepted_stems(run_name)
    rows, drop_stats = filter_rows(meta_files, stems_ok, revalidate_code=True)
"""

from __future__ import annotations

import datetime
import signal
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SYNTH_CSV = ROOT / "data" / "data_generation" / "synth_parts.csv"
# Canonical blocklist: stems dropped by the upload filter, readable by UI.
BLOCKLIST_CSV = ROOT / "data" / "data_generation" / "upload_blocklist.csv"

# Sticky exec-validation columns in synth_parts.csv. Preserved across runs so
# future pushes skip already-checked stems. Not uploaded to HF.
EXEC_CACHE_COLS = ("code_exec_ok", "code_exec_reason", "code_exec_checked_at")

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


def _load_exec_cache() -> dict[str, tuple[str, str]]:
    """Return {stem: (ok_str, reason)} from CSV — "" if column missing/empty."""
    if not SYNTH_CSV.exists():
        return {}
    df = pd.read_csv(SYNTH_CSV)
    for c in EXEC_CACHE_COLS:
        if c not in df.columns:
            return {}
    oks = df["code_exec_ok"].fillna("").astype(str)
    rsn = df["code_exec_reason"].fillna("").astype(str)
    return {s: (ok, r) for s, ok, r in zip(df["stem"], oks, rsn) if isinstance(s, str)}


def _write_exec_cache(updates: dict[str, tuple[str, str]]) -> None:
    """Merge {stem: (ok_str, reason)} into synth_parts.csv. In-place.

    Uses vectorized map + fillna to avoid pandas LossySetitemError when the
    existing column was inferred as float64 from all-empty cells.
    """
    if not updates or not SYNTH_CSV.exists():
        return
    df = pd.read_csv(SYNTH_CSV)
    for c in EXEC_CACHE_COLS:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str).replace("nan", "")
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    ok_map = {s: ok for s, (ok, _) in updates.items()}
    reason_map = {s: r for s, (_, r) in updates.items()}
    df["code_exec_ok"] = df["stem"].map(ok_map).fillna(df["code_exec_ok"]).astype(str)
    df["code_exec_reason"] = (
        df["stem"].map(reason_map).fillna(df["code_exec_reason"]).astype(str)
    )
    df.loc[df["stem"].isin(updates), "code_exec_checked_at"] = ts
    df.to_csv(SYNTH_CSV, index=False)


_CHECKPOINT_PATH = ROOT / "tmp" / "exec_cache_checkpoint.jsonl"


def _checkpoint_append(updates: dict[str, tuple[str, str]]) -> None:
    """Append a JSONL line per update. Side-channel for crash recovery."""
    import json as _json

    _CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CHECKPOINT_PATH, "a") as f:
        for stem, (ok, reason) in updates.items():
            f.write(_json.dumps({"stem": stem, "ok": ok, "reason": reason}) + "\n")


def _load_checkpoint() -> dict[str, tuple[str, str]]:
    """Return accumulated {stem: (ok, reason)} from checkpoint JSONL (if any)."""
    import json as _json

    out: dict[str, tuple[str, str]] = {}
    if not _CHECKPOINT_PATH.exists():
        return out
    with open(_CHECKPOINT_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                d = _json.loads(line)
                out[d["stem"]] = (d["ok"], d.get("reason", ""))
            except Exception:
                continue
    return out


def revalidate_exec(
    pairs: list[tuple[str, Path]],
    workers: int = 8,
    use_cache: bool = True,
) -> dict[str, str]:
    """Return {stem: reason} for stems whose code.py fails to exec under current env.

    When use_cache=True, reads synth_parts.csv.code_exec_ok — skips True, records
    False from cache, only executes unchecked stems. Writes results back to CSV.
    """
    # Merge persistent CSV cache + any crash-recovery checkpoint.
    cache = _load_exec_cache() if use_cache else {}
    if use_cache:
        cache.update(_load_checkpoint())

    to_run: list[tuple[str, Path]] = []
    bad: dict[str, str] = {}
    for stem, code_path in pairs:
        ok, reason = cache.get(stem, ("", ""))
        if ok == "True":
            continue
        if ok == "False":
            bad[stem] = reason or "cached_exec_fail"
            continue
        to_run.append((stem, code_path))

    if cache:
        n_hit = sum(1 for s, _ in pairs if cache.get(s, ("", ""))[0] == "True")
        n_bad_cache = sum(1 for s, _ in pairs if cache.get(s, ("", ""))[0] == "False")
        print(
            f"    cache: {n_hit} pass / {n_bad_cache} fail / {len(to_run)} to run",
            flush=True,
        )

    updates: dict[str, tuple[str, str]] = {}
    pending_checkpoint: dict[str, tuple[str, str]] = {}
    if to_run:
        with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as pool:
            futs = {pool.submit(_exec_code, p): p[0] for p in to_run}
            done = 0
            n = len(to_run)
            for fut in as_completed(futs):
                try:
                    stem, reason = fut.result(timeout=_EXEC_TIMEOUT_SEC * 4)
                except Exception as e:
                    stem = futs[fut]
                    reason = f"worker_err:{type(e).__name__}"
                if reason:
                    bad[stem] = reason
                    updates[stem] = ("False", reason)
                    pending_checkpoint[stem] = ("False", reason)
                else:
                    updates[stem] = ("True", "")
                    pending_checkpoint[stem] = ("True", "")
                done += 1
                if done % 500 == 0 or done == n:
                    new_bad = sum(1 for v in updates.values() if v[0] == "False")
                    print(
                        f"    exec-check [{done}/{n}] new bad: {new_bad}",
                        flush=True,
                    )
                # Incremental checkpoint every 2000 to survive crashes.
                if use_cache and len(pending_checkpoint) >= 2000:
                    _checkpoint_append(pending_checkpoint)
                    pending_checkpoint.clear()

    if use_cache and pending_checkpoint:
        _checkpoint_append(pending_checkpoint)

    if use_cache and updates:
        _write_exec_cache(updates)
        print(f"    wrote exec cache for {len(updates)} stems", flush=True)
        # Cache persisted to CSV — checkpoint now redundant.
        try:
            _CHECKPOINT_PATH.unlink()
        except FileNotFoundError:
            pass

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
