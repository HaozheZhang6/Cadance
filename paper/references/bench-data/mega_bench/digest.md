# mega_bench — MEGA-Bench: Scaling Multimodal Evaluation to over 500 Real-World Tasks

**Venue:** ICLR 2025 · **Year:** 2025 · **URL:** https://tiger-ai-lab.github.io/MEGA-Bench/ · **PDF:** raw.pdf

## TL;DR
505 real-world multimodal tasks (≈8,000 samples) spanning images/videos/3D/UI/document inputs and free-form/numeric/code/coordinate/JSON outputs, scored by 45 custom metrics — first benchmark to break out of multiple-choice for MLLMs.

## Storyline (5-piece)
- **Problem.** Existing MLLM benches (MMMU, MMT-Bench, MMBench) lock everything into 4-option MCQ to ease grading, killing generative ability evaluation; running 27 separate benches per Qwen2-VL release is unmanageable, redundant, and biased.
- **Contribution.** MEGA-Bench unifies 505 distinct real-world tasks under one taxonomy tree (application × input type × output format × required skill); 16 expert annotators contribute tasks via a GUI; 45 custom metrics cover number/phrase/code/LaTeX/coordinate/JSON/free-form outputs; resulting fine-grained capability report along multiple orthogonal dimensions.
- **Evidence (approach).** Iterative taxonomy refinement, contributor review (initial submission, model-test review, periodic audit) ensures novelty/quality. Annotation GUI standardizes JSON task spec; visualization web-tool checks output.
- **Experiments.** Evaluate flagship (GPT-4o, Claude-3.5 Sonnet, Gemini-1.5 Pro/Flash) + open (Qwen2-VL, InternVL2, LLaVA-OneVision) + efficiency models. Claude-3.5 Sonnet ≈ GPT-4o (<0.1% diff); Qwen2-VL leads open by ~10%; CoT helps proprietary, hurts 10/13 open models.
- **Analysis.** Capability radar across application/input/output/skill axes shows Claude wins planning+math+UI, GPT-4o wins info-extract+knowledge; reveals that single-score leaderboards mask huge per-axis variance.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 1 | tree + samples | taxonomy | Taxonomy tree (application/skill) + 6 example tasks across input modalities. | Defines coverage and breadth. |
| 2 | 4 | flow diagram | pipeline | Annotation GUI → JSON spec → metric assignment → review. | How 16 annotators built 505 tasks. |
| 3 | 6 | nested ring | data-stats | Distribution of tasks by input/output type, application, skill. | Balanced coverage; output diversity vs MCQ benches. |
| 4 | 8 | results table | headline-results | Per-model overall + per-axis scores; flagship vs open vs efficiency. | Claude-3.5 ≈ GPT-4o; Qwen2-VL leads open. |
| 5 | 9 | radar | radar-comparison | Per-axis radar comparing 5 flagship models. | Each model wins different axes; aggregate scores hide it. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow per-axis radar: BenchCAD should report per-axis (family / difficulty / view-count / metric-type) radar — much more informative than single number.
- Borrow custom-metric philosophy: don't force code generation into pass/fail; design metrics for parametric IoU, syntax validity, exec validity, view fidelity, and topology match.
- Borrow CoT-helps-proprietary-hurts-open finding as ablation template for BenchCAD: log whether CadCoT prompting helps each model, expect similar split.
- Borrow taxonomy-tree visualization for paper Fig 1: hierarchical tree of CAD families/operations/difficulty serves as instant visual TL;DR.
- Avoid: 505-task scale not necessary; CAD has tighter task definition. We borrow structure not breadth.

## One-line citation
Chen et al., "MEGA-Bench: Scaling Multimodal Evaluation to over 500 Real-World Tasks," ICLR 2025.
