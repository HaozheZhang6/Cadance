# infinity_chat — Infinity-Chat: An Open-Ended Generation Benchmark Reveals Artificial Hivemind in Large Language Models

**Venue:** NeurIPS D&B (Best Paper) · **Year:** 2025 · **URL:** https://arxiv.org/abs/2510.22954 · **PDF:** raw.pdf

## TL;DR
26K real WildChat-mined open-ended prompts + 31,250 dense human annotations (25 per item) across 70+ LMs reveal an "Artificial Hivemind": both intra-model repetition and, more critically, inter-model homogeneity that means model ensembles don't actually diversify outputs.

## Storyline (5-piece)
- **Problem.** Open-ended generation evals are stuck on toy tasks (random number, persona, poetry). No real-world prompt corpus exists for measuring diversity / pluralism / mode collapse. Existing diversity studies use single-model self-sampling and miss the cross-model picture.
- **Contribution.** (i) **Infinity-Chat dataset**: 26K real-world open-ended user queries mined from WildChat with no single ground truth; (ii) **first comprehensive open-ended taxonomy** with 6 top-level categories (Creative Content, Brainstorm & Ideation, Speculative & Hypothetical, Skill Development, etc.) → 17 subcategories; (iii) **31,250 dense human annotations** (absolute ratings + pairwise prefs, **25 annotators per item**); (iv) systematic study of 70+ LMs revealing the "Artificial Hivemind" phenomenon (intra-model + inter-model collapse); (v) evidence that LM-judges and reward models miscalibrate against idiosyncratic human preferences.
- **Evidence (approach).** Mined WildChat dialogs → filtered for open-ended (multi-valid-answer) prompts → expert-coded 6×17 taxonomy → sampled 50 responses per model per query at top-p=0.9, T=1.0 → PCA over sentence embeddings to visualize cluster structure → 25 independent annotators per (query, response) for ratings.
- **Experiments.** 25 LMs in main paper (70+ in appendix). Diversity = embedding cluster spread; quality = human rating; calibration = LM-judge accuracy on pairwise prefs.
- **Analysis.** Iconic "time is a river" finding: 25 different LMs prompted "Write a metaphor about time" all converge to two clusters dominated by river/weaver imagery. Human preferences for these responses are idiosyncratic (Cohen's κ low across annotators) — yet LM-judges are confident. Calibration is worst exactly where annotators disagree.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | PCA scatter | hero | "Time is a river" — 25 LMs × 50 samples cluster into 2 dominant centers | Iconic mode collapse visualization |
| 2 | 3 | tree | taxonomy | 6 top-level × 17 subcategory open-ended prompt taxonomy | First taxonomy of open-endedness |
| 3 | 5 | bar | data-stats | 26K queries / 31,250 annotations / 25 annotators per item | Annotation density |
| 4 | 7 | matrix/heat | headline-results | Pairwise inter-model similarity across 70+ LMs | Inter-model homogeneity quantified |
| 5 | 9 | scatter | human-vs-model | LM-judge agreement vs annotator-disagreement | Calibration breaks where preferences diverge |

## Takeaways for BenchCAD
- **Iconic single hero-figure** ("time is a river" PCA) is the Best-Paper-winning move: ONE memorable image that demos the phenomenon and the dataset value at once. We need this for BenchCAD — e.g. "what does GPT-5 think a hex_nut looks like" PCA across 100 model samples.
- **6-category × 17-subcategory taxonomy** is the right grain (not too many, not too few). Our 106 family registry is the right base; cluster into 6–10 macro-categories for the headline tax-tree.
- **25 annotators per item** is overkill for IoU eval but essential for *open-ended* sub-tasks (e.g. "generate 5 alternative chair designs"). Good template if we add an open-ended slice.
- **LM-judge calibration check** is a reviewer-killer: any benchmark using LLM-as-judge needs to show calibration vs human preference per slice; we currently use rule-based metrics so this isn't urgent but useful for future "design quality" extension.
- **Borrow** the framing "we're studying X, and we discovered Y as a byproduct" — the Hivemind discovery isn't the contribution but it sells the dataset. We can position our cross-family transfer findings the same way.

## One-line citation
Zhao et al. (2025). Infinity-Chat: An Open-Ended Generation Benchmark Reveals Artificial Hivemind in Large Language Models. NeurIPS D&B 2025 (Best Paper).
