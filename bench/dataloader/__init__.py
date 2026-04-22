"""Dataset loading — HuggingFace or local run directory."""

from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from pathlib import Path


def load_hf(
    repo: str,
    split: str = "test",
    token: str | None = None,
    shuffle_seed: int | None = None,
) -> list[dict]:
    """Load one split from an HF dataset repo (default split = 'test').

    shuffle_seed: if set, shuffle rows deterministically (same seed → same order).
    """
    from datasets import load_dataset

    token = token or os.environ.get("BenchCAD_HF_TOKEN") or os.environ.get("HF_TOKEN")
    ds = load_dataset(repo, token=token)
    rows = list(ds[split])
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(rows)
    return rows


def stratified_sample(rows: list[dict], per_family: int) -> list[dict]:
    by_fam: dict[str, list] = defaultdict(list)
    for r in rows:
        by_fam[r["family"]].append(r)
    return [r for fam_rows in by_fam.values() for r in fam_rows[:per_family]]


def load_done_stems(out_path: Path) -> set[str]:
    done: set[str] = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["stem"])
                except Exception:
                    pass
    return done
