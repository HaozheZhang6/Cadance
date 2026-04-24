"""Deterministic, family-aware row sampling for bench runners.

Goals:
- Same `(rows, n, seed, key)` → exact same output list (and order).
- For small `n` (≤ 200): plain shuffle + head — efficient, fine for smoke tests.
- For large `n` (> 200): stratified — every value of `stratify_key` gets at
  least one slot, then remaining capacity is filled proportional to family size.
- Independent of input row order: rows are pre-sorted by `id_key` first, so
  HuggingFace shuffle / append order doesn't perturb the result.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

STRATIFY_THRESHOLD = 200


def _id(row: dict, id_key: str) -> str:
    """Stable per-row identity for canonicalising input order."""
    v = row.get(id_key)
    if v is None:
        # fallback chain: stem → record_id → str(row)
        v = row.get("stem") or row.get("record_id") or repr(sorted(row.items()))
    return str(v)


def sample_rows(
    rows: list[dict],
    n: int,
    seed: int,
    *,
    stratify_key: str = "family",
    id_key: str = "stem",
    threshold: int = STRATIFY_THRESHOLD,
) -> list[dict]:
    """Return up to `n` rows. n<=0 → all rows (sorted by id_key).

    n <= threshold: shuffle(seed) + head(n).
    n  > threshold: stratified — 1-per-stratum base, then proportional fill.
    """
    if not rows:
        return []
    canon = sorted(rows, key=lambda r: _id(r, id_key))
    if n <= 0 or n >= len(canon):
        return canon

    rng = np.random.default_rng(seed)
    if n <= threshold or stratify_key not in canon[0]:
        order = rng.permutation(len(canon))
        return [canon[i] for i in order[:n]]

    return _stratified(canon, n, rng, stratify_key)


def _stratified(
    canon: list[dict], n: int, rng: np.random.Generator, key: str
) -> list[dict]:
    by_strat: dict[Any, list[dict]] = defaultdict(list)
    for r in canon:
        by_strat[r[key]].append(r)

    # Deterministic stratum order: sort by name so output is reproducible
    strata = sorted(by_strat.keys(), key=str)

    # Shuffle within each stratum once (deterministic per seed)
    for s in strata:
        order = rng.permutation(len(by_strat[s]))
        by_strat[s] = [by_strat[s][i] for i in order]

    if n < len(strata):
        # Cannot give 1 per stratum → pick first n strata, take 1 each
        return [by_strat[s][0] for s in strata[:n]]

    # Base layer: 1 per stratum
    selected: list[dict] = [by_strat[s][0] for s in strata]
    remaining = n - len(strata)

    # Pool of leftovers, proportional fill via a single deterministic shuffle
    leftover: list[dict] = []
    for s in strata:
        leftover.extend(by_strat[s][1:])
    if remaining and leftover:
        order = rng.permutation(len(leftover))
        selected.extend(leftover[i] for i in order[:remaining])
    return selected
