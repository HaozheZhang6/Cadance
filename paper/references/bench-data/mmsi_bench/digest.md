# mmsi_bench — MMSI-Bench: A Benchmark for Multi-Image Spatial Intelligence

**Venue:** ICLR 2026 · **Year:** 2026 · **URL:** https://runsenxu.com/projects/MMSI_Bench · **PDF:** raw.pdf · **arXiv:** 2505.23764

## TL;DR
1,000 fully human-curated multi-image spatial-reasoning MCQs across 11 task
types with step-by-step reasoning; humans 97.2% vs GPT-5 41.9% vs best
open-source 30.7% — the largest spatial human–model gap on record.

## Storyline (5-piece)
- **Problem.** Spatial intelligence is essential for embodied AGI but
  existing multi-image benchmarks are templated (VSI-Bench, MMIU) or treat
  spatial only as a sub-split (BLINK, MuirBench). The only fully
  human-curated set, ERQA, has just 113 multi-image items — far below
  reviewer expectation for a D&B paper.
- **Contribution.** A 3-element × 3-dimension taxonomy
  (camera / object / region × position / attribute / motion) yielding 10
  atomic + 1 multi-step-reasoning task. Every question carries a
  step-by-step reasoning annotation that doubles as quality control and as
  input to an automated error-analysis pipeline.
- **Evidence (approach).** 6 researchers × 300+ hours inspect 120K
  candidate images from 8 source datasets (ScanNet, nuScenes, Matterport3D,
  Ego4D, AgiBot-World, DTU, DAVIS, Waymo). 4-stage pipeline: collect → MCQ
  authoring → 3-reviewer audit → difficulty calibration via human answering
  time. Avg 2.55 images per question, max 10.
- **Experiments.** 37 MLLMs evaluated alongside 3 baselines (random, blind
  GPT-4o, human). GPT-5 41.9%, o3 41.0%, Qwen2.5-VL-72B 30.7%,
  NVILA-15B beats most 70B+ models. Qwen2.5-VL 72B vs 32B differs by 3 pts;
  InternVL3-78B vs 1B differs by 1.5% — a clear scaling cliff.
- **Analysis.** Chain-of-thought helps GPT-4o slightly and hurts everything
  else; visual prompting also fails to close the gap. Four named error
  modes (grounding, overlap-matching, situation-transformation,
  spatial-logic). Automated error pipeline using reasoning anno reaches 78%
  agreement.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | hero composite | hero | task examples + error pie + model bar w/ human line | sells diversity, difficulty, gap |
| 2 | 4 | example grid | taxonomy | one representative QA per of 11 categories | makes 11-task taxonomy concrete |
| 3 | 5 | flow diagram | pipeline | 4-stage construction (collect, annotate, audit, calibrate) | rigor narrative |
| 4 | 6 | results table | headline-results | 11-col × 37-row Table 3 with proprietary / open / baseline groups | full evaluation, human bottom row |
| 5 | 8 | qualitative + bar | failure-cases | 4 named error types with examples + per-model error distribution | structural failure analysis |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **Steal the 3 × 3 taxonomy structure.** Pair (input-modality ×
  output-modality × reasoning-depth) so reviewers see systematic, not
  ad-hoc, coverage. Each cell maps to one BenchCAD task variant.
- **"Fully human-curated" as moat.** Match with "20K parts × IoU≥0.99
  verified × 106 families × 8 industrial domains"; verification rigor
  itself becomes a contribution.
- **Reasoning annotations are dual-use.** Used for QC and as input to an
  automated error-analysis pipeline. Our verified GT (CadQuery + STEP +
  4-view + parameter table) plays the same multi-purpose role across all 5
  BenchCAD tasks; advertise this dual use.
- **Scaling-cliff punchline.** "78B vs 1B = +1.5%" is ICLR-grade; replicate
  by sweeping a code-LM family (Qwen2.5-Coder 0.5/1.5/7/32B) on CAD codegen
  — if scaling fails to lift parametric accuracy, that's our headline.
- **Error-type cataloguing > raw acc bars.** Name 4 CAD error modes
  (wrong primitive, wrong topology, wrong dimension, wrong constraint) and
  show stacked-bar per model.

## One-line citation
Yang, S., Xu, R., Xie, Y., Yang, S., Li, M., Lin, J., Zhu, C., Chen, X.,
Duan, H., Yue, X., Lin, D., Wang, T., Pang, J. (2026).
*MMSI-Bench: A Benchmark for Multi-Image Spatial Intelligence.* ICLR 2026.
