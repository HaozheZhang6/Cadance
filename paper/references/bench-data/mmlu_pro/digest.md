# mmlu_pro — MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark

**Venue:** NeurIPS 2024 D&B Spotlight · **Year:** 2024 · **URL:** https://openreview.net/forum?id=y10DM6R2r3 · **PDF:** raw.pdf

## TL;DR
12,032 reasoning-heavy MCQs across 14 disciplines with 10 distractors (vs MMLU's 4) — drops top-model accuracy 16-33%, halves prompt-sensitivity, and finally makes CoT *help* instead of *hurt*.

## Storyline (5-piece)
- **Problem.**
  - MMLU is the de-facto LLM benchmark but is saturated: GPT-4 86.4% (Mar 2023) → GPT-4o 87.4% (May 2024), basically no headroom in a year.
  - Prompt-fragile: ±4-5% swing across 24 paraphrased prompts on the same model.
  - Noisy: a non-trivial portion of original MMLU items are mislabeled or unanswerable, capping the achievable ceiling.
  - 4-option format is gameable; CoT *hurts* on MMLU because knowledge-shortcuts beat deliberate reasoning.
- **Contribution.**
  - 14 broader disciplines (vs MMLU's 57 narrow categories) for cleaner aggregation.
  - Reasoning-focused additions sourced from STEM-Website, TheoremQA, SciBench.
  - **10 answer options** instead of 4 — 3× more distractors → harder to guess, harder to game.
  - Two-pass expert review removing wrong answers, false-negative options, and bad-format items.
- **Evidence (approach).**
  - 4-stage construction pipeline (Fig 2): (1) **Initial filter** — drop MMLU items 4+ of 8 small models answer correctly (5,886 removed); (2) **Integrate** — extract short answers + 3 distractors via GPT-4-Turbo; (3) **Option augment** — expand 4→10 options with GPT-4-Turbo distractors; (4) **Expert review** Phase 1 = correctness/format, Phase 2 = Gemini-1.5-Pro flags possible false-negatives → humans adjudicate.
  - Issue table (Table 1) reports per-source counts: 350 incorrect MMLU answers, 1953 false-negatives in MMLU options, 862 bad questions on STEM-Website.
- **Experiments.**
  - 50+ models evaluated 5-shot CoT (Gemini-1.5 0-shot).
  - GPT-4o 72.6%, GPT-4-Turbo 63.7%, Claude-3-Opus close behind; gap to MMLU = 16-33%.
  - Discriminability: GPT-4o vs GPT-4-Turbo gap **1% → 9%** moving from MMLU to MMLU-Pro.
  - Prompt sensitivity: ±4-5% → ±2%.
  - CoT now boosts GPT-4o by 19% (vs hurting on MMLU) — confirms reasoning is the new axis.
- **Analysis.**
  - Error analysis on 120 GPT-4o errors: **39%** reasoning flaws, **35%** missing domain knowledge, **12%** computation, rest misc.
  - Open-source (Llama-3-70B, DeepSeek-V2) approach Claude-Sonnet but trail Opus/4o.
  - CoT-vs-Direct gap is a *property of the benchmark*, not just the model — argues MMLU-Pro is reasoning-real.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig01 | 1 | Triple panel | hero | MMLU vs MMLU-Pro: difficulty gap, prompt-sensitivity profile, CoT vs Direct | Sells all three claims in one image — headline contribution graphic |
| fig04 | 4 | Pipeline | pipeline | 4-stage construction: filter → collect → augment → review | Methodology cookbook readers will copy |
| fig06 | 6 | Table | headline-results | Per-discipline accuracy for ~25 models, CoT, 5-shot | Headline numbers + ranking discriminability evidence |
| fig08 | 8 | Bar | ablation | Score distribution under 24 prompt variants per model | Quantifies the robustness gain over MMLU |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Three-claim hero figure.**
  - MMLU-Pro's Fig 1 packs (a) difficulty gap (b) robustness (c) reasoning unlock into one panel.
  - BenchCAD should design a single Fig 1 making 3 differentiating claims at once vs Text2CAD / CAD-Recode (e.g. geometric-IoU gap, prompt-paraphrase robustness, multi-step boolean unlock).
- **Frame "discriminability" as a first-class metric.**
  - They quantify bench quality by *spread between top models* (1%→9%).
  - BenchCAD: report IoU spread across frontier models, argue our bench separates them better than existing CAD benches.
- **Two-phase expert review is the credibility lever.**
  - Phase 1 humans verify correctness; Phase 2 a SoTA model flags suspicious distractors then humans confirm.
  - Cheap, thorough, defensible. Mirror for CAD GT verification (geometry-correctness pass + LM-flagged-ambiguity pass).
- **Construction pipeline as a §3 figure, not buried in text.**
  - Visualizing the funnel makes the dataset feel rigorous and gives reviewers something to cite.
- **Error taxonomy with percentages.**
  - "39% reasoning / 35% knowledge / 12% computation" is actionable for model devs.
  - BenchCAD analog: wrong-primitive / wrong-dim / wrong-bool / wrong-pattern / wrong-axis with explicit fractions.
- **Quantify the construction effort.**
  - Issue-counts table (Table 1) signals how much human work went in. Borrow.

## One-line citation
Wang et al., "MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark," NeurIPS 2024 D&B.
