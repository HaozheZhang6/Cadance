"""Sample family + difficulty from config mix."""

import numpy as np


def sample_family(family_mix: dict, rng: np.random.Generator) -> str:
    """Sample a family name according to the configured mix weights."""
    names = list(family_mix.keys())
    weights = np.array([family_mix[n] for n in names], dtype=float)
    weights /= weights.sum()
    return rng.choice(names, p=weights)


def sample_difficulty(difficulty_mix: dict, rng: np.random.Generator) -> str:
    """Sample a difficulty level according to the configured mix weights."""
    levels = list(difficulty_mix.keys())
    weights = np.array([difficulty_mix[l] for l in levels], dtype=float)
    weights /= weights.sum()
    return rng.choice(levels, p=weights)
