"""UA-28: build qixiaoqi/cad_bench_50 from qixiaoqi/cad_bench_200.

Pick 50 families uniformly at random (seed=42) from the 106 families in cad_bench_200,
then 1 stem per family (deterministic). Push to HF as qixiaoqi/cad_bench_50 (split=train).
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from datasets import load_dataset

SRC = "qixiaoqi/cad_bench_200"
DST = "qixiaoqi/cad_bench_50"
SEED = 42
N_FAMILIES = 50

token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
ds = load_dataset(SRC, split="train", token=token)
print(f"loaded {SRC}: {len(ds)} rows, fields={ds.column_names}")

by_fam: dict[str, list[int]] = defaultdict(list)
for i, fam in enumerate(ds["family"]):
    by_fam[fam].append(i)
families = sorted(by_fam.keys())
print(f"total families: {len(families)}")

rng = np.random.default_rng(SEED)
fam_perm = rng.permutation(len(families))
chosen_families = sorted(families[i] for i in fam_perm[:N_FAMILIES])
print(f"chosen {len(chosen_families)} families:")
for f in chosen_families:
    print(f"  {f}")

chosen_idx = []
for fam in chosen_families:
    cands = by_fam[fam]
    pick = cands[int(rng.integers(0, len(cands)))] if len(cands) > 1 else cands[0]
    chosen_idx.append(pick)
chosen_idx.sort()

sub = ds.select(chosen_idx)
print(f"subset: {len(sub)} rows")

local_dir = ROOT / "data" / "data_generation" / "cad_bench_50_local"
local_dir.mkdir(parents=True, exist_ok=True)
sub.save_to_disk(str(local_dir))
print(f"saved local Arrow → {local_dir}")

print(f"pushing to {DST} ...")
sub.push_to_hub(DST, split="train", token=token, private=False)
print("✓ push done")
