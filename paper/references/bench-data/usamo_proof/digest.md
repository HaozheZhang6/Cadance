# usamo_proof — Proof or Bluff? Evaluating LLMs on 2025 USA Math Olympiad

**Venue:** ICML 2025 AI4MATH workshop / OpenReview 2025 · **Year:** 2025 · **URL:** https://matharena.ai/ · **PDF:** raw.pdf

## TL;DR
Expert human-graded full-proof evaluation of 11 frontier reasoning LLMs on the 6 freshly-released USAMO 2025 problems: best model (Gemini-2.5-Pro / DeepSeek-R1 05/28) scores < 30 %, most < 5 %.

## Storyline (5-piece)
- **Problem.** AIME-style benchmarks score only final numerical answers and saturate (Gemini-2.5-Pro, o4-mini); they reward correct guesses despite flawed proofs. No benchmark stresses rigorous proof reasoning on uncontaminated problems.
- **Contribution.** First proof-evaluation framework run within hours of competition release: 4 IMO-team-level human judges, IMO-style 7-point rubric, 4 runs/model, double-blind grading; per-error category taxonomy (Logic / Assumption / Creativity / Algebra-Arithmetic).
- **Evidence (approach).** USAMO 2025 6 problems × 11 models × 4 runs ≈ 264 graded solutions; rubric drawn from AoPS community; double-grader IMO protocol; 24-hour grading window prevents data-leakage rebuttal.
- **Experiments.** Eleven reasoning LLMs (QwQ, R1, R1-0528, Gemini-2.5-Pro, Flash-Thinking, o1-pro, o3, o3-mini, o4-mini, Grok-3, Claude-3.7) graded; cost in USD reported; paired permutation test for rank confidence.
- **Analysis.** Top-4 cluster (R1-0528 12.8/42, Gemini-2.5-Pro 10.1, o3 9.2, o4-mini 8.1); rest ≤2/42; only 1 perfect 7/7 (Grok-3 on P1). LLM judges (o4-mini, o3-mini, Claude-3.7) inflate scores ≤20× and show OpenAI bias → automatic grading not yet viable. Common artifacts: forced \boxed{} answers, "trivially" skipped steps, monolithic strategy with no creativity.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| fig02_hero | 2 | sample problems | hero | USAMO 2025 P1 + P5 statements | Difficulty + proof-style requirement (no boxed answer expected). |
| fig04_headline-results | 4 | main table | headline-results | Per-problem and total scores for 11 models | Best 12.8/42 ≈ 30 %; majority below 5 %; cost column. |
| fig05_failure-cases | 5 | stacked bar | failure-cases | Distribution of first-failure category per model | Logic dominates; o3-mini "trivializes"; R1 has many algebra slips. |
| fig06_human-vs-model | 6 | secondary results table | human-vs-model | Auto-grader scores vs human (Table 2) | LLM judges over-estimate by 2–20×; o4-mini closest yet biased. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow **fresh / contamination-proof problem release** — tie a slice of BenchCAD test set to a release window or hold-out post date to track future contamination.
- Borrow **error taxonomy** (Logic / Assumption / Creativity / Algebra) → CAD analogue: Topology / Constraint-violation / Wrong-feature / Numeric-dim error; enables qualitative diagnosis beyond IoU.
- Borrow **double-blind expert grading** for a small "proof-of-CAD-intent" qualitative subset (e.g., 60 designs) to complement automatic IoU/CD metrics.
- Borrow **rank-significance via paired permutation test** — sample size matters; report CIs on model ranks rather than raw means.
- Avoid LLM-as-judge for high-stakes correctness — show inflation factors as cautionary baseline.

## One-line citation
Petrov, I. et al. "Proof or Bluff? Evaluating LLMs on 2025 USA Math Olympiad." ICML 2025 AI for Math Workshop.
