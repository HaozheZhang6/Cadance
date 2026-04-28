# bbeh — BIG-Bench Extra Hard

**Venue:** arXiv 2025 (Google DeepMind tech report) · **Year:** 2025 · **URL:** https://github.com/google-deepmind/bbeh · **PDF:** raw.pdf

## TL;DR
23-task drop-in replacement for BBH, each task harder counterpart probing the same skill family; best general-purpose model 9.8 % harmonic-mean accuracy, best reasoning model 44.8 %.

## Storyline (5-piece)
- **Problem.** BBH (saturated >90 %) was the de-facto general-reasoning benchmark; reasoning evaluation now skews toward math/code while logic, temporal, spatial, humour, causal skills are under-tested.
- **Contribution.** BBEH replaces every one of the 23 BBH tasks with a same-domain but significantly harder task (e.g. BoardgameQA replaces Logical Deduction, Buggy Tables replaces Penguins-in-a-Table); 200 examples/task (120 for Disambig-QA); plus BBEH-Mini (460 ex) for cheap sweeps; preserves automatic deterministic scoring.
- **Evidence (approach).** Semi-adversarial construction loop: iterate task design until both Gemini-1.5-Flash and Gemini-Thinking-Exp score <70 %; expand skill set to 12 capabilities (many-hop, long-context, going-against-prior, learning-on-the-fly, etc.); average context length ×6, output length ×7 vs BBH.
- **Experiments.** 13 models from Llama-3.1, Qwen-2.5, Gemma-2/3, Gemini-2.0, GPT-4o, R1-Distill-32B, DeepSeek-R1, o3-mini-high; report per-task accuracy and harmonic-mean; report BBEH-Mini.
- **Analysis.** Reasoning models help on logic/math-heavy tasks but barely move the needle on humour, sarcasm, world-knowledge tasks; harmonic mean penalises lopsided strengths and surfaces blind spots invisible in macro-average.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| fig01_hero | 1 | horizontal bar | hero | Harmonic-mean accuracy across 10 models | General models ≤9.8 %; o3-mini-high 44.8 %; large headroom. |
| fig04_taxonomy | 4 | grid of task samples | taxonomy | Ten BBEH task examples (Spatial, BoardgameQA, …) | Illustrates skill diversity and prompt format. |
| fig07_data-stats | 7 | log-bar chart | data-stats | Avg input length BBEH vs BBH per task | Inputs ~6× longer; matches "real-world reasoning" claim. |
| fig09_headline-results | 9 | results table | headline-results | Per-task accuracy across 13 models | Wide variance per task; harmonic-mean kills outlier-driven means. |
| fig11_ablation | 11 | grouped bars | ablation | Reasoning-model gains by skill category | Big gains on logic/math; small/negative on humour/world-knowledge. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow **harmonic-mean** as a primary metric across CAD families — penalises models that ace simple primitives but fail on assemblies/booleans, mirroring "general reasoning" goal.
- Borrow **same-domain-but-harder replacement** — for BenchCAD, design v2 families that iterate on existing ones (e.g. "Hard-Bracket": same primitive, more booleans + tighter tolerance) rather than only adding new families.
- Borrow **semi-adversarial construction loop** with two reference models (one cheap, one strong) until both <70 % — a cheap recipe for guaranteeing benchmark longevity.
- Borrow **Mini split** (~20/family) for fast iteration; full set for leaderboard.
- Avoid: sole reliance on macro-average accuracy; report per-skill and harmonic; otherwise saturation looks closer than it is.

## One-line citation
Kazemi, M. et al. "BIG-Bench Extra Hard." arXiv:2502.19187, May 2025.
