# blink — BLINK: Multimodal Large Language Models Can See but Not Perceive

**Venue:** ECCV 2024 · **Year:** 2024 · **URL:** https://zeyofu.github.io/blink/ · **PDF:** raw.pdf · **arXiv:** 2404.12390

## TL;DR
BLINK recasts 14 classic CV perception tasks (depth, correspondence, jigsaw,
multi-view, forensics) into 3,807 MCQs with visual prompts; humans 95.7% vs
GPT-4V 51.3% — perception abilities have not "emerged" in current MLLMs.

## Storyline (5-piece)
- **Problem.** MLLMs are evaluated on language-mediated VQA, but core visual
  perception (relative depth, dense correspondence, multi-view geometry,
  forensics) resists clean text mediation. Existing suites (MMMU, MathVista,
  ScienceQA) reward language reasoning over fine perception, hiding this gap.
- **Contribution.** A 14-task suite spanning pixel-level to image-level
  perception, low-level to mid-level reasoning. Each task is reformatted into
  an MCQ paired with visual prompts (circles, points, arrows) so any
  general-purpose MLLM can answer with no API change. Total 3,807 questions
  drawn from 7 image domains.
- **Evidence (approach).** Each task is derived from a classic CV benchmark
  (NYUv2 for depth, MegaDepth/ScanNet for correspondence, NIST for forensics,
  Objaverse for multi-view). Visual prompts overlay the pixel-level query so
  the question reduces to "which of A/B/C is closer / same / real".
- **Experiments.** 17 MLLMs including GPT-4V, Gemini-Pro, Qwen-VL-Max,
  LLaVA-1.6 family, plus a strong CV specialist baseline and human
  performance. Humans 95.7%, GPT-4V 51.3% (+13 over random), Gemini-Pro 45.7%;
  CV specialists beat MLLMs by 20–40 pts on every perception axis.
- **Analysis.** Concatenating multiple images into one input hurts; scaling
  model size barely helps within a family; CoT prompting yields tiny gains.
  The specialist-vs-MLLM gap suggests perception is missing as a capability,
  not as a scale or prompt issue.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | composite teaser | hero | 14-task icon grid with one MCQ each | sells task diversity in one panel |
| 2 | 3 | comparison table | gap-vs-prior | BLINK vs MMMU / MathVista / SEED on perception axes | positions BLINK as perception-only, multi-image, prompt-driven |
| 3 | 6 | stats panel | data-stats | task count, image-domain pie, prompt-type bar | scope and balanced coverage |
| 4 | 7 | bar chart | headline-results | per-task accuracy, MLLM vs human vs random | exposes the human–model gap task-by-task |
| 5 | 8 | qualitative grid | case-study | per-task example with 4-MLLM and human predictions | concrete failure modes per perception axis |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **Classic-CV-recast-as-MCQ trick.** Translate hard CAD perception
  ("which face is bigger?", "is this hole through-or-blind?",
  "are these two edges parallel?") into MCQ with visual prompts so
  non-specialist MLLMs can be probed without bespoke decoders.
- **Human-vs-model gap as headline.** BLINK pins 95.7 vs 51.3 on the cover;
  BenchCAD should pin a comparable expert-vs-SOTA gap, e.g. on parametric
  correctness or family-match accuracy, ideally above 50 pts.
- **Specialist baseline matters.** BLINK shows CV specialists beat MLLMs by
  20–40 pts; we should add a CAD-specialist baseline (CAD-Recode,
  Text2CAD-tuned, fine-tuned Qwen2.5-Coder) to argue parametric pre-training
  is the missing ingredient.
- **Avoid the 14-task overload.** High task cardinality dilutes narrative and
  forces busy hero figures. Keep BenchCAD at 5 tasks with a single-row hero.
- **Prompt-format reuse.** Visual prompts (red circles, A/B markers) transfer
  directly to our 4-view renders for "which view shows feature X" queries.

## One-line citation
Fu, X., Hu, Y., Li, B., Feng, Y., Wang, H., Lin, X., Roth, D., Smith, N.A.,
Ma, W.-C., Krishna, R. (2024). *BLINK: Multimodal Large Language Models Can
See but Not Perceive.* ECCV 2024.
