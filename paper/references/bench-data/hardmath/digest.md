# hardmath — HARDMath: A Benchmark Dataset for Challenging Problems in Applied Mathematics

**Venue:** ICLR 2025 · **Year:** 2024/2025 · **URL:** https://github.com/sarahmart/HARDMath · **PDF:** raw.pdf

## TL;DR
1,466 algorithmically generated graduate-level applied-math problems (asymptotic / approximation methods) with numerically-validated ground truth; GPT-4 5-shot CoT 43.8 %, o1-mini 62.3 %, Llama-3-8B 20.2 %.

## Storyline (5-piece)
- **Problem.** Existing math benchmarks (MATH, GSM8K, MathQA, JEEBench) are grade-/high-school and focus on closed-form problems; advanced applied-math reasoning that requires asymptotic approximation, dominant-balance heuristics and tool use is absent.
- **Contribution.** Synthetic generator producing 4 problem classes (Nondim / Polynomial roots / ODEs / Integrals incl. Laplace) with 7 sub-types + 40 hand-crafted contextual word problems; LaTeX problem + step-by-step solution + numerical verification per problem; HARDMath-Mini (366 ex) for evaluation.
- **Evidence (approach).** SymPy + SciPy pipeline: random coefficients → algorithmic solution → analytic vs numerical relative error <10 % filter; semi-automated visual plot verification; LLM-generated word-problem context with plausibility-checker LLM (>0.5 score keep).
- **Experiments.** GPT-3.5 / GPT-4 / o1-mini (closed) and Llama-3-8B / CodeLlama-13B (open) under 0/1/5-shot CoT; LLM-procedural-grader (GPT-4o) plus SymPy answer matcher; 40-problem applied-context word-problem suite for GPT-4 (28.1 % accuracy).
- **Analysis.** ODEs hardest (≤30 %); Nondim easiest; few-shot CoT helps most for GPT-4 / o1-mini; common error modes = wrong dominant balance, missing regimes, dropping imaginary roots; o1-mini still far below MATH-500 baseline (62 vs 90 %), confirming benchmark difficulty.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| fig01_hero | 1 | title page | hero | Paper header + abstract framing | Establishes asymptotic-methods focus and scale (1.4k problems). |
| fig03_data-stats | 3 | dual pie | data-stats | HARDMath-Mini vs full HARDMath composition | Per-problem-type proportions (Nondim/Roots/ODEs/Integrals). |
| fig04_pipeline | 4 | flowchart | pipeline | Algorithmic generation pipeline (Fig. 2) | Coefficients → SymPy solve → numerical check → keep if <10 % err. |
| fig08_headline-results | 8 | results table | headline-results | Accuracy by model × problem type × shots | o1-mini 62.3, GPT-4 43.8, Llama-3-8B 20.2; ODEs lag everywhere. |
| fig09_failure-cases | 9 | bars + pie | failure-cases | Correct / partial / incorrect + GPT-4 root-finding error modes | CoT shifts errors to "missing dominant balance" rather than wrong answers. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow **algorithmic problem generator with numerical ground-truth verifier** — direct analogue to BenchCAD's CadQuery-build + IoU verifier; cite this as precedent that synthetic benchmarks can be peer-reviewed top-tier.
- Borrow **error-tolerance threshold** (<10 % rel-err) as a transparent acceptance gate analogous to IoU≥0.99 / volume tolerance.
- Borrow **LLM-as-procedural-grader** for partial credit on multi-step CAD construction (with manual sub-sample validation), to capture intermediate sketch correctness beyond final geometry.
- Borrow **scale + Mini split** philosophy (1.4k full, 366 mini) — matches our 100k synthetic + ~1.5k curated bench design.
- Contrast: HARDMath problems are pure text math; BenchCAD must additionally verify visual / geometric correctness — emphasise that step in our pitch.

## One-line citation
Fan, J. et al. "HARDMath: A Benchmark Dataset for Challenging Problems in Applied Mathematics." ICLR 2025. arXiv:2410.09988.
