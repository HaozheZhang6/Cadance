"""Per-(task, model) results directory with append-only dedup.

Layout:
    results/<task>/<model_slug>/
        results.jsonl               one line per sample, dedup key=`id_key`
        codes/<key>.py              optional gen artifacts
        steps/<key>.step
        renders/<key>/              dir of PNGs
        runs/<ts>__seed<seed>__N<n>.json    invocation provenance

The same (task, model) is a single growing pool: re-running with a
different seed/N just expands the pool. Each invocation drops a sidecar
JSON in `runs/` recording exactly which keys it intended to evaluate.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
RESULTS_ROOT = ROOT / "results"


def slug(s: str) -> str:
    return s.replace(":", "_").replace("/", "_").replace(" ", "_")


class ResultsDir:
    """Manages results/<task>/<model>/ ."""

    def __init__(self, task: str, model: str, root: Path | None = None):
        self.task = task
        self.model = model
        self.root = (root or RESULTS_ROOT) / task / slug(model)
        self.results_path = self.root / "results.jsonl"
        self.codes = self.root / "codes"
        self.steps = self.root / "steps"
        self.renders = self.root / "renders"
        self.runs = self.root / "runs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs.mkdir(parents=True, exist_ok=True)
        self._fh = None

    # ── done-set / dedup ──────────────────────────────────────────────────

    def done_keys(self, id_key: str = "stem") -> set[str]:
        done: set[str] = set()
        if not self.results_path.exists():
            return done
        with open(self.results_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                v = rec.get(id_key)
                if v is not None:
                    done.add(str(v))
        return done

    # ── append + artifacts ────────────────────────────────────────────────

    def open(self) -> ResultsDir:
        if self._fh is None:
            self._fh = open(self.results_path, "a")
        return self

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def append(self, rec: dict) -> None:
        self.open()
        self._fh.write(json.dumps(rec) + "\n")
        self._fh.flush()

    def save_code(self, key: str, code: str) -> Path:
        self.codes.mkdir(parents=True, exist_ok=True)
        p = self.codes / f"{key}.py"
        p.write_text(code)
        return p

    def save_step(self, key: str, src_path: str | Path) -> Path:
        self.steps.mkdir(parents=True, exist_ok=True)
        p = self.steps / f"{key}.step"
        shutil.copyfile(src_path, p)
        return p

    def save_render_dir(self, key: str, src_dir: str | Path) -> Path:
        target = self.renders / key
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src_dir, target)
        return target

    # ── provenance ────────────────────────────────────────────────────────

    def log_run(
        self,
        argv: dict,
        sampled: Iterable[dict] | None = None,
        id_key: str = "stem",
    ) -> Path:
        """Drop runs/<ts>__seed<seed>__N<n>.json with sampling config + key list."""
        ts = time.strftime("%Y%m%dT%H%M%S")
        seed = argv.get("seed", "?")
        n = argv.get("limit") or argv.get("n") or 0
        keys = []
        if sampled is not None:
            keys = [str(r.get(id_key)) for r in sampled if r.get(id_key) is not None]
            n = n or len(keys)
        path = self.runs / f"{ts}__seed{seed}__N{n}.json"
        path.write_text(
            json.dumps(
                {
                    "ts": ts,
                    "task": self.task,
                    "model": self.model,
                    "argv": argv,
                    "n_sampled": len(keys),
                    "keys": keys,
                },
                indent=2,
            )
        )
        return path

    # ── helpers for runner __exit__ ───────────────────────────────────────

    def __enter__(self) -> ResultsDir:
        return self.open()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
