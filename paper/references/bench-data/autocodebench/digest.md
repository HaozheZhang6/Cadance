# autocodebench — AutoCodeBench: Large Language Models are Automatic Code Benchmark Generators

**Venue:** ICLR 2026 · **Year:** 2025 (arXiv 2508.09101) · **URL:** https://arxiv.org/abs/2508.09101 · **PDF:** raw.pdf

## TL;DR
Reverse-order LLM-Sandbox interaction synthesizes a 3,920-problem, 20-language, human-free code benchmark on which the best LLM hits only 52.4 average Pass@1, leaving large headroom (upper bound 74.8).

## Storyline (5-piece)
- **Problem.** Code benchmarks are either Python-only (HumanEval / MBPP / LiveCodeBench) or multilingual but manually curated and unbalanced (MultiPL-E / FullStackBench / McEval); none combines high difficulty, balanced language coverage, and zero human annotation.
- **Contribution.** AutoCodeGen pipeline + AutoCodeBench (3,920 problems, 20 langs, 14 categories) + Lite (1,586 high-discrimination items) + Complete (1,000 base-model 3-shot items) + open-source 20-language sandbox.
- **Evidence (approach).** 4-step reverse pipeline: (1) Solution Gen seeded from Stack-Edu, (2) LLM emits test inputs → sandbox executes solution to capture outputs → assemble test function, (3) Problem Gen back-derives problem statement, (4) filtering by multi-sample difficulty / LLM-critic / tag-balanced sampling.
- **Experiments.** 30+ open and proprietary LLMs (1.5B–1T) on Pass@1; multi-logical subset (1,622 items); param/sample scaling; multi-turn refinement with sandbox feedback; AutoCodeBench-Complete on base models with 3-shot.
- **Analysis.** 87.6% human verification on 6 langs; explicit DeepSeek-bias study; Lite widens model gaps; refinement loops give DeepSeek-V3 +11.6 pts in 3 turns; popular vs. low-resource gap persists.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 3 | radial bars + difficulty pie | data-stats | Language / category / difficulty distribution of ACB and ACB-Lite | Balanced 20 langs, 14 tag groups, 60%+ hard |
| 2 | 4 | pipeline diagram | pipeline | Four-stage AutoCodeGen flow with sandbox interaction | Solution → test fn → problem → filtering |
| 3 | 7 | model × language matrix | headline-results | Pass@1 of 30+ LLMs across 20 languages on ACB | Claude Opus 4 Think tops at 52.4 avg; upper bound 74.8 |
| 4 | 9 | line plots | ablation | Param scaling and sandbox-feedback multi-turn refinement | DeepSeek-V3 48.1→59.7 over 3 turns |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Lite/Complete split — a high-discrimination subset for fast leaderboards plus a base-model few-shot variant cleanly separates instruct vs. base evaluation; mirror as BenchCAD-Lite (~500 parts) + BenchCAD-Edit / QA single-task subsets.
- **Borrow:** Difficulty calibrated by N-pass sampling of a fixed model (here DeepSeek-Coder-V2-Lite, 10 samples → 0/1-5/>5 = hard/med/easy). Ground-truth-execution-based labels, not human ratings.
- **Borrow:** "Upper bound = union of best models" framing (74.8 vs. 100) underscores headroom — apply to our 5-task aggregate IoU / score.
- **Contrast:** They synthesize problems from real code seeds; we synthesize parts procedurally from a family registry — both are human-free but ours guarantees executable ground truth via CadQuery, no LLM critic needed.
- **Avoid:** Single-vendor LLM critics introduce family-bias risk; AutoCodeBench mitigates with cross-model push-pull. We should pre-empt with an explicit family-bias / model-bias section.

## One-line citation
AutoCodeBench [Chou et al., ICLR 2026] uses LLM-sandbox interaction to auto-build a 3,920-problem 20-language benchmark where SOTA LLMs reach only 52.4 Pass@1, validating execution-grounded synthesis as a scalable alternative to manual curation.
