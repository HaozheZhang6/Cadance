# mmmu_pro — MMMU-Pro: A More Robust Multi-discipline Multimodal Understanding Benchmark

**Venue:** ACL 2025 (also ICLR 2025 submission) · **Year:** 2025 · **URL:** https://mmmu-benchmark.github.io · **PDF:** raw.pdf

## TL;DR
MMMU-Pro hardens MMMU by removing text-only-solvable items, expanding options to 10, and adding a vision-only screenshot setting; performance drops 16.8–26.9% across all frontier MLLMs.

## Storyline (5-piece)
- **Problem.** MMMU scores (GPT-4o 69.1%) suggest near-human multimodal reasoning, but models may exploit text-only shortcuts and 4-option guessing rather than truly seeing.
- **Contribution.** Three-step robustification on top of MMMU: (1) filter questions answerable by 4 text-only LLMs in ≥2/4 attempts, (2) augment from 4→up to 10 candidate options, (3) introduce vision-only setting where the question is rendered as a photo/screenshot containing both text and image.
- **Evidence (approach).** Start from 10,500 MMMU val/test items; LLM-filter to 5,919 image-dependent ones; human validators re-pick 1,730 truly visual; GPT-4-turbo + human edits expand options. Vision-only renders questions with diverse fonts/backgrounds simulating real screenshots.
- **Experiments.** Evaluate ~20 proprietary + open MLLMs (GPT-4o, Claude-3.5, Gemini-1.5, InternVL2, LLaVA-OneVision, Qwen2-VL, etc.). All models drop substantially: GPT-4o 69.1→51.9, Claude-3.5 68.3→51.5; smaller open models drop further.
- **Analysis.** CoT prompting helps almost every model (avg +2–4 pts) on standard split but mixed on vision-only; explicit OCR prompts give ~0% gain — modern MLLMs already OCR implicitly, but reading text inside complex visual scenes is the actual bottleneck. Failure-case analysis shows models miss spatial layout cues that humans resolve trivially.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 1 | flow diagram | pipeline | LLM filter → option augment → photo/screenshot rendering. | Three construction stages turning MMMU into MMMU-Pro. |
| 3 | 3 | qualitative | vision-only | Two MMMU-Pro items rendered as screenshot vs photo with question embedded. | Defines the new vision-only input format. |
| 5 | 5 | bar chart | headline-results | Per-model accuracy on MMMU vs MMMU-Pro Standard vs Vision. | 16.8–26.9 pt drops; ranks reshuffle vs original MMMU. |
| 6 | 6 | grouped bars | ablation | CoT vs direct prompting across models on both splits. | CoT gain consistent on Standard, smaller/mixed on Vision. |
| 7 | 7 | qualitative | failure-cases | GPT-4o errors on chart/diagram/photo items with reasoning trace. | Models hallucinate text positions when scene is cluttered. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow the "filter shortcuts" recipe: run a text-only baseline (CadQuery LLM with no image) on every benchmark item; drop those it solves at chance — proves CAD bench really requires vision.
- Borrow option augmentation analogue: in CAD, expand parametric distractors (10 plausible dim sets, only one matches GT) so guessing is costly — converts free-form into discriminative scoring.
- Borrow framing of "performance drop %" as the headline metric: report drop from "easy" (text+JSON+image) to "hard" (image-only) for every model — reviewers love a single big number.
- Contrast: MMMU-Pro relies on multi-choice; CAD code-gen is generative. We cannot reuse option augmentation directly — must report exact-IoU + parametric Hausdorff instead.
- Avoid: don't repeat their finding that "OCR prompts don't help" — irrelevant to CAD; instead test analogue "explicit primitive list prompts don't help".

## One-line citation
Yue et al., "MMMU-Pro: A More Robust Multi-discipline Multimodal Understanding Benchmark," ACL 2025.
