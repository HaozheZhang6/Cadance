# BenchCAD Scoring — single source of truth

Every img2cq bench run produces one row per stem. Every stem row has these 7 columns; the **final score** is a fixed linear combination of the first 6.

| # | Column | Range | What it measures |
|---|---|---|---|
| 1 | **`iou`** | [0, 1] | Voxel IoU @ 64³ between gen STEP and gt STEP, both normalized (bbox center → [0.5]³, longest → [0,1]³). Fixed orientation. |
| 2 | **`iou_rot24`** (a.k.a. `iou_rot` when `--rot-invariant 24`) | [0, 1] | Max IoU over the 24-element axis-aligned cube rotation group. Robust to the model picking a different "up". |
| 3 | **`cd_score`** (raw saved as `chamfer`) | [0, 1] | Bidirectional Chamfer distance (2048 sampled points). Raw distance preserved in `chamfer` field; `cd_score = cd_to_score(chamfer)` is the mapped [0, 1] value used in the final score (lower CD ↔ higher score). |
| 4 | **`hd_score`** (raw saved as `hausdorff`) | [0, 1] | Hausdorff distance. Raw distance preserved in `hausdorff` field; `hd_score = hd_to_score(hausdorff)` is the mapped [0, 1] value used in the final score. |
| 5 | **`essential_pass`** | {0, 1, N/A} | Hand-curated per-family op check (`bench/research/canonical_ops.yaml`, loaded by `bench/research/canonical_ops.py`). 1 if every essential AND-element is satisfied by gen ops, 0 if any missing, **N/A** for the 13 families with no canonical essential. |
| 6 | **`feature_f1`** | [0, 1] | F1 over `{has_chamfer, has_fillet, has_hole}` indicators (independent of essential). |
| 7 | **`score`** | [0, 1] | Final — linear combination of 1–6. |

## Final score formula

```text
score = 0.60·IoU                  ← max(iou, iou_rot24) when rot24 is computed
      + 0.20·essential_pass
      + 0.10·feature_f1
      + 0.05·cd_score
      + 0.05·hd_score
```

Total weights = 1.0. Implemented in `bench/metrics/combined_score()`.

**N/A handling**: when `essential_pass = None` (family has no canonical essential), drop the 0.20 essential term and **rescale by ×1.25** so the remaining 0.80 weight covers the full [0, 1] range. Equivalent to treating the dropped 0.20 share as evenly redistributed across the other components — N/A samples are not penalized OR boosted relative to non-N/A samples that score the same on the other 0.80.

### Why this split

- **0.60 geometry** (max of raw IoU and 24-rotation IoU): single dominant term — geometric fidelity is the headline metric; rotation-invariant preferred when computed.
- **0.20 essential**: hard semantic check — model used the canonically-required op for this family (e.g. `sweep+helix` for `torsion_spring`). Catches cases where IoU is decent but model used a substitute op (anti-shortcut signal). Rescaled away when N/A.
- **0.10 feature_f1**: orthogonal feature presence check (chamfer / fillet / hole). Light tiebreaker.
- **0.05 + 0.05 cd / hd**: surface-level fidelity. Small weight because highly correlated with IoU.

## Edge cases

| Scenario | Behavior |
|---|---|
| Generated code fails to exec | `iou = iou_rot24 = cd_score = hd_score = 0`. `feature_f1` and `essential_pass` still computed from `gen_code` text. Partial-credit fallback: `score = 0.10·feature_f1 + 0.20·ess` (max 0.3); N/A scaling still applies. |
| GT exec fails | Same as above. Drop the sample from the run (rare). |
| `--rot-invariant` not used | `iou_rot` is None → `IoU` term in formula uses raw `iou`. |
| Family is N/A in `bench/research/canonical_ops.yaml` | `essential_pass = None` → drop 0.20 term, multiply remaining sum by **1.25** to renormalize. 13 N/A families: `chair`, `dowel_pin`, `i_beam`, `parallel_key`, `stepped_shaft`, `table`, `wall_anchor`, `clevis_pin`, `round_flange`, `t_pipe_fitting`, `tee_nut`, `phone_stand`, `pull_handle`. |

## Per-stem result schema (`results/<task>/<model>/results.jsonl`)

Each line:
```json
{
  "stem": "synth_torsion_spring_000980_s4252",
  "family": "torsion_spring",
  "difficulty": "hard",
  "exec_ok": 1,

  "iou": 0.029,
  "iou_rot": 0.029,        // present only when --rot-invariant 24 was passed
  "iou_rot_idx": 0,

  "chamfer": 0.0461,
  "hausdorff": 0.273,
  "cd_score": 0.31,
  "hd_score": 0.40,

  "essential_pass": false, // True / False / null
  "feature_f1": 0.667,

  "score": 0.314           // computed via combined_score(...)
}
```

## Standard report table (recommended layout for paper / Discord posts)

Per model, aggregate over the run:

| metric | mean | notes |
|---|---|---|
| exec rate | % stems where `exec_ok = 1` | gating |
| **iou** | mean over all (failed-exec → 0) | column 1 |
| **iou_rot24** | mean over all | column 2 |
| **chamfer** (mm) | mean over exec_ok | raw distance — diagnostic |
| **cd_score** | mean over all | column 3 (mapped, used in final) |
| **hausdorff** (mm) | mean over exec_ok | raw distance — diagnostic |
| **hd_score** | mean over all | column 4 (mapped, used in final) |
| **essential pass rate** | (# pass) / (# non-N/A stems) | column 5 (skip N/A in denominator) |
| **feature_f1** | mean over all | column 6 |
| **final score** | mean of `score` field | column 7 |

Convention: report the `_score` columns in main paper tables (uniform [0, 1]); keep raw `chamfer` and `hausdorff` (mm) in supplementary / debug tables for diagnostic detail. Both are saved per stem in `results/<task>/<model>/results.jsonl`.

For comparison tables across models, all 7 columns should be reported. Don't average iou_rot24 across some N/A condition — every stem has it.

## Computing `essential_pass` offline

```python
from bench.research.canonical_ops import find_ops, essential_pass

pass_or_none = essential_pass(family, find_ops(gen_code))
```

## Aggregation across stems for the cohort-level final score

```python
from bench.metrics import combined_score

scores = [
    combined_score(
        feature_f1=r["feature_f1"],
        iou=r["iou"],
        cd=r["chamfer"],
        hd=r["hausdorff"],
        essential_pass=r.get("essential_pass"),
        iou_rot=r.get("iou_rot"),
    )
    for r in results
]
mean_final = sum(scores) / len(scores)
```

## Versioning

Score formula and `bench/research/canonical_ops.yaml` are versioned together. Any change to weights or essential specs must be commented in the PR; existing `results/<task>/<model>/results.jsonl` from older runs may need re-scoring (the per-stem fields are stable; only `score` changes).
