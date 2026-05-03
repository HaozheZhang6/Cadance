# mmiu — MMIU: Multimodal Multi-Image Understanding for Evaluating Large Vision-Language Models

**Venue:** ICLR 2025 · **Year:** 2025 · **URL:** https://mmiu-bench.github.io · **PDF:** raw.pdf

## TL;DR
77K images / 11K MCQs across 7 multi-image relationship types and 52 tasks —
the most extensive multi-image benchmark of its kind; even GPT-4o reaches
only 55.7%, with spatial multi-image tasks the dominant weakness.

## Storyline (5-piece)
- **Problem.** Multi-image VQA is critical for real-world LVLMs (multi-view,
  video-frame, diagram, GUI navigation) but evaluation lags single-image.
  Prior multi-image suites (Video-MME, MIRB, MUIRBENCH, MileBench) cover
  narrow scope and miss spatial / 3D / GUI relationships.
- **Contribution.** A hierarchical taxonomy with 7 multi-image relationship
  types — low-level, semantic, spatial, temporal, 3D, multi-view, GUI etc.
  — partitioned into 52 fine-grained tasks. 11,698 MCQs assembled over
  77,659 images sourced from existing datasets.
- **Evidence (approach).** Pipeline: (i) refine task pool from prior
  literature, (ii) scrape source datasets, (iii) generate MCQ via GPT-4 with
  human review, (iv) audit for relationship correctness. Tasks tagged along
  low-vs-high-level and subject-vs-object axes.
- **Experiments.** ~30 LVLMs including GPT-4o (55.7%), Gemini, InternVL,
  LLaVA-NeXT, Mantis, Qwen-VL. Gap > 40 pts between best proprietary and
  worst open-source. Spatial relationships are uniformly hardest.
- **Analysis.** Per-task heatmap reveals weakness clusters (3D, multi-view,
  spatial). Strong single-image models do not transfer; longer context
  length partially helps; multi-image specialised pretraining (M4-Instruct,
  Mantis-Instruct) gives modest gains.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | radial taxonomy | hero | 7-relationship ring with example per slice | conveys taxonomy + scale at a glance |
| 2 | 2 | comparison table | gap-vs-prior | MMIU vs Video-MME / MIRB / MUIRBENCH / MileBench | argues most extensive |
| 3 | 4 | flow diagram | pipeline | task refinement → data collection → MCQ generation → audit | data-construction rigor |
| 4 | 6 | results table | headline-results | per-relationship accuracies for ~30 LVLMs | spatial tasks worst across the board |
| 5 | 8 | scatter / cluster | correlation | model-cluster vs task-cluster heatmap | identifies capability deficiencies by group |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **Multi-relationship taxonomy ring.** Visually compact way to sell N task
  types; we can adapt to BenchCAD's 5 tasks × difficulty grid using a ring
  or radar layout.
- **Aggregation > collection.** MMIU mostly reuses existing datasets and
  contributes the task framing. We already do this with Fusion360 +
  DeepCAD + synthetic families — this is an established precedent.
- **Per-relationship breakdown over single accuracy.** Replicate with
  per-family or per-task accuracy tables to surface weakness clusters
  rather than collapsing into one number.
- **Avoid 52 tasks.** That cardinality drew reviewer pushback for redundancy
  and overlap; keep BenchCAD's task list short, deeply justified, with no
  task that another covers.
- **GPT-4o ceiling 55.7% framing.** A single sticky number works as a bench
  headline; we should pin one such number ("best SOTA scores X% IoU on
  parametric reconstruction") for the abstract.

## One-line citation
Meng, F., Wang, J., Li, C., Lu, Q., Tian, H., Liao, J., Zhu, X., Dai, J.,
Qiao, Y., Luo, P., Zhang, K., Shao, W. (2025). *MMIU: Multimodal Multi-Image
Understanding for Evaluating Large Vision-Language Models.* ICLR 2025.
