"""Generate 106 single-family configs for the 180k data-arg expansion (UA-24).

Each family gets its own config with:
- num_samples = 1900 (target ~1700 accepted at ~92% rate, total ~180k+)
- seed deterministic per family (avoids overlap with seed 4252 used by replace41)
- run_name = data_arg_180k_<family>  (family-scoped resume)
- param_scale enabled [0.8, 1.2]
- dedup_params on
"""

import hashlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.data_generation.cad_synth.pipeline.registry import (  # noqa: E402
    list_families,
)

NUM_SAMPLES = 1900
SEED_BASE = 5000


def family_seed(name: str) -> int:
    h = hashlib.md5(name.encode()).hexdigest()
    return SEED_BASE + (int(h[:8], 16) % 10000)


def main() -> None:
    families = list_families()
    print(f"Generating {len(families)} configs in {ROOT}")
    for fam in families:
        cfg = {
            "run_name": f"data_arg_180k_{fam}",
            "num_samples": NUM_SAMPLES,
            "seed": family_seed(fam),
            "n_workers": 4,
            "family_mix": {fam: 1},
            "difficulty_mix": {"easy": 1, "medium": 1, "hard": 1},
            "render": True,
            "param_scale": {"enabled": True, "lo": 0.8, "hi": 1.2},
            "dedup_params": True,
        }
        path = ROOT / f"{fam}.yaml"
        with open(path, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"Done. Total: {len(families)} configs.")


if __name__ == "__main__":
    main()
