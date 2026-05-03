# spatialqa — SpatiaLQA: A Benchmark for Evaluating Spatial Logical Reasoning in Vision-Language Models

**Venue:** arXiv 2026 (under review) · **Year:** 2026 · **URL:** https://github.com/xieyc99/SpatiaLQA · **PDF:** raw.pdf · **arXiv:** 2602.20901

## TL;DR
9,605 QA pairs over 241 real indoor scenes targeting *spatial logical
reasoning* (multi-step task plans grounded in 3D scene relations); 41 VLMs
evaluated, all struggle; the authors propose recursive scene-graph-assisted
reasoning that outperforms baselines.

## Storyline (5-piece)
- **Problem.** Standard VQA tests perception, common logical reasoning
  tests symbolic chains, but neither tests joint spatial-understanding +
  multi-step logic — e.g. "to pick up the bottom book, which obstacles
  must be moved first and in what order?". EQA is the closest neighbour
  but uses a closed motor-primitive vocabulary, so it does not probe
  open-vocabulary reasoning over scene relations.
- **Contribution.** SpatiaLQA: 9,605 QA over 241 indoor scenes covering
  object-relation queries, ordered-step planning, and precondition
  graphs (open-vocabulary outputs). Includes 41-model evaluation and a
  Recursive Scene-Graph (RSG) prompting method that decomposes the scene
  into a task-relevant subgraph before reasoning.
- **Evidence (approach).** Scenes drawn from existing 3D indoor datasets
  (point-cloud + RGB). QA generated semi-automatically with GPT and then
  human-verified. Tasks include ordered step plans whose precondition DAG
  is the GT, allowing structural rather than string evaluation.
- **Experiments.** GPT-4o, Gemini, Claude, Qwen2.5-VL, InternVL,
  LLaVA-NeXT — 41 VLMs total. Best closed-source still significantly
  below human; open-source much worse on logical-step tasks. Method
  ablation isolates each RSG component.
- **Analysis.** RSG prompting consistently improves base VLMs by 5–15 pts;
  scene-graph granularity matters (too coarse loses detail, too fine
  overwhelms the prompt). Method generalises across all 41 backbones,
  suggesting the bottleneck is *prompt structure*, not model capability.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | three-panel teaser | hero | common VQA / common logical / spatial-logical examples with GPT-4o failures | defines the gap visually |
| 2 | 4 | flow diagram | pipeline | scene → object detection → recursive graph → step plan | RSG method overview |
| 3 | 5 | stats panel | data-stats | 9.6K QA, 241 scenes, task-type distribution | data scale |
| 4 | 6 | results table | headline-results | 41 VLMs across QA categories | broad evaluation, gap to human |
| 5 | 7 | ablation table | ablation | RSG component ablation, granularity sweep | each component contributes |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **"X is critical but underexplored" framing** with side-by-side
  comparison teaser (Common-VQA / Common-Logical / Ours) — CAD-codegen
  analogue: VQA / single-view CAD / parametric multi-view CAD; one figure
  positions us against two adjacent fields.
- **Open-vocabulary output > MCQ** for advanced reasoning. They argue MCQ
  caps cognitive challenge; for BenchCAD, code is naturally open-vocab,
  which validates our task framing against pure-MCQ benchmarks.
- **41-model sweep** is a high bar for "extensive evaluation"; confirms
  30+ as a minimum bar for ICLR / NeurIPS D&B in 2026.
- **Method + bench combo.** Papers including a baseline method get higher
  acceptance odds; consider a "scene-graph"-style CAD-prompting baseline
  (multi-view → constraint graph → code) shipped alongside BenchCAD.
- **Avoid layout pitfall.** A 41-model table is hard to read at 6 pt; if
  we copy this format, split closed/open-source across two tables and put
  full table in appendix.

## One-line citation
Xie, Y., Zhang, X., Shan, Y., Hao, Z., Tang, R., Wei, R., Song, M.,
Wan, Y., Song, J. (2026). *SpatiaLQA: A Benchmark for Evaluating Spatial
Logical Reasoning in Vision-Language Models.* arXiv 2602.20901.
