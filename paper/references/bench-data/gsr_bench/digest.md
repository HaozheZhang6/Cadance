# gsr_bench — GSR-Bench: A Benchmark for Grounded Spatial Reasoning Evaluation via Multimodal LLMs

**Venue:** NeurIPS 2024 Workshop (Compositional Learning) · **Year:** 2024 · **URL:** arXiv 2406.13246 · **PDF:** raw.pdf

## TL;DR
Extends What'sUp with bbox + segmentation + monocular-depth annotations, then evaluates 9 MLLMs (7B–110B) under multiple-choice, template-generation (CircularEval), grounding, and depth-augmented prompting — finding that LLaMA-3-LLaVA-NeXT-8B reaches 86.1% with only 1.1% loss vs the 4.25× larger 34B model.

## Storyline (5-piece)
- **Problem.** Existing spatial-relation evals (What'sUp etc.) ignore grounding (where is the object?) and depth, and use bias-prone Vanilla MC eval. Compositional reasoning conflates recognition + relation.
- **Contribution.** GSR-Bench: extended What'sUp with (1) GroundingDINO bboxes, (2) SAM masks, (3) ZoeDepth maps. Evaluates 18 VLMs + 9 MLLMs across MC + Template-Generation w/ CircularEval; depth-augmented prompting variant.
- **Evidence (approach).** Subset A: on/under/left/right relative to chairs/tables; Subset B: in-front/behind/left/right on tabletops; COCO-Spatial + GQA-Spatial one-obj/two-obj subsets. Templates ask "object is (X) other-object" with 4 options. CircularEval requires correctness across all 4 permutations.
- **Experiments.** Models: LLaVA-1.5/1.6 family (7B/13B/34B), LLaMA-3-LLaVA-NeXT-8B, InternVL-1.5-26B, LLaVA-NeXT-Qwen-110B + 18 VLMs from What'sUp. TG (Table 1) and grounding (Table 2 — IoU ≥ 0.5). Depth hint via avg-depth-value augmentation.
- **Analysis.** MC suffers from option-position bias, esp. small models; large models robust. Generative MLLMs jump from <61% (CLIP/BLIP era) to >85%; LLaMA-3-LLaVA-NeXT-8B sweet-spot. Models can answer correctly without grounding correctly — failure mode quantified. Depth prompts help disambiguate front/behind.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 1 | 1 | bench summary | hero | LLaMA-3-LLaVA-NeXT-8B 86.1% headline vs XVLM 60.4% on What'sUp | Generation MLLMs close the spatial gap |
| 2 | 2 | prompting pipeline | pipeline | TG prompt; depth-augmented prompt with ZoeDepth values | Standard + depth-hint prompting |
| 3 | 3 | TG results table | headline-results | Per-subset accuracies for 9 MLLMs + 18 VLMs | Quantitative ranking |
| 5 | 5 | grounding table | ablation | IoU≥0.5 vs GroundingDINO across subsets | Decoupling recognition from grounding |
| 6 | 6 | failure / depth analysis | failure-cases | Cases where model answers correctly but grounding fails or depth helps | Where current MLLMs still break |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: CircularEval — permute every multiple-choice question across all positions and require all-correct; eliminates option-letter bias. Critical for fair CAD MC eval.
- Borrow: report decoupled metrics — recognition (does it see the part?) vs reasoning (does it produce the right code?). Mirrors GSR's grounding-vs-relation split.
- Contrast: GSR is binary spatial relation; CAD code-gen is open-ended generation — CircularEval doesn't apply directly, but the bias awareness does.
- Borrow: include an auxiliary-modality (depth) prompt variant — for CAD analog: provide section views or B-rep snippets and measure whether MLLMs use them.
- Avoid: drawing strong conclusions from <100-sample subsets (What'sUp Subset B is small) — for BenchCAD ensure subset sizes ≥500 per skill.

## One-line citation
Rajabi & Košecká, "GSR-Bench: A Benchmark for Grounded Spatial Reasoning Evaluation via Multimodal LLMs," NeurIPS 2024 Workshop on Compositional Learning.
