# scicode — SciCode: A Research Coding Benchmark Curated by Scientists

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://scicode-bench.github.io · **PDF:** raw.pdf

## TL;DR
80 multi-step research-coding problems (338 subproblems) curated by PhD-level scientists across 16 sub-fields where the best LLM (o1-preview) solves only 7.7% of main problems.

## Storyline (5-piece)
- **Problem.** General code benchmarks (HumanEval, MBPP, even APPS) saturate quickly and ignore the long-horizon, knowledge-heavy programming that real scientists do day-to-day.
- **Contribution.** SciCode: scientist-curated, hierarchically decomposed benchmark with main problems → subproblems → tests, plus optional scientific-background prompts; covers math / physics / chem / bio / mat-sci / EE / geo (16 sub-fields).
- **Evidence (approach).** PhD-level annotators write each problem from real research / influential papers, supply gold solutions and multiple unit tests, double-review for correctness; tasks are decomposed so partial credit is measurable.
- **Experiments.** Evaluate proprietary (GPT-4o, Claude-3-Opus/3.5-Sonnet, Gemini-1.5, o1-preview) and open (DeepSeek-Coder-V2, Llama-3-70B, Mixtral-8x22B, Qwen2-72B) on main vs. subproblem accuracy, with/without background, with gold vs. generated dependencies.
- **Analysis.** Even o1-preview hits 7.7% main / 28.5% sub; background prompts give consistent gains (best model → 12.3% main); open models often score 0% main while passing some subproblems — integration is the bottleneck.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | task schematic | hero | Main problem decomposed into 3 subproblems with docstrings + background | How a SciCode item is structured |
| 2 | 4 | annotation pipeline | data-stats | Curation flow: scientist authoring, gold solution, test-case writing, review | Quality-control loop |
| 3 | 5 | sub-field bar / pie | taxonomy | Distribution of 80 problems across 16 scientific sub-fields | Field coverage breadth |
| 4 | 7 | results table | headline-results | Pass rates on main vs. subproblem across 11 LLMs | o1-preview 7.7%/28.5%; open models 0% main |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Hierarchical decomposition. CAD parts naturally split into operations (sketch → extrude → fillet → boolean) — score per-operation IoU as well as final-part IoU, exposing partial competence the way SciCode's subproblems do.
- **Borrow:** "With / without background" toggle. For BenchCAD, evaluate with vs. without geometric hints (named features / dimension table) to measure how much grounding LLMs need.
- **Borrow:** Expert-curated quality bar. Even procedurally generated CAD should include a scientist-curated subset (~50–100 parts) with engineer-written specs to act as the high-trust core leaderboard, mirroring SciCode's PhD-curation.
- **Contrast:** SciCode is small (80 main / 338 sub) due to expert cost; we can use procedural sampling for scale (~10k parts) and reserve manual curation for QA/edit annotation.
- **Avoid:** Reporting only final-task accuracy — many models pass subproblems but fail main; we should always show op-level + part-level metrics side-by-side.

## One-line citation
SciCode [Tian et al., NeurIPS 2024 D&B] is a 80-main / 338-sub problem benchmark across 16 natural-science fields where the best model (o1-preview) solves only 7.7% of main problems, demonstrating that scientist-authored multi-step research code remains far from saturated.
