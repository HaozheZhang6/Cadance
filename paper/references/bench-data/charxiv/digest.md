# charxiv — CharXiv: Charting Gaps in Realistic Chart Understanding in Multimodal LLMs

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://charxiv.github.io · **PDF:** raw.pdf

## TL;DR
2,323 hand-curated arXiv charts with descriptive + reasoning QA expose a much larger proprietary↔open MLLM gap (GPT-4o 47.1% vs InternVL-1.5 29.2% reasoning) than prior synthetic chart benchmarks suggest, with all models far below human 80.5%.

## Storyline (5-piece)
- **Problem.** Existing chart benchmarks (FigureQA, DVQA, ChartQA) use synthetic or template charts and template questions; on these open-source MLLMs appear to match or beat proprietary ones — a stress test (slight chart/question perturbation) drops SPHINX-V2 by 34.5 pts, exposing the appearance as artifact.
- **Contribution.** CharXiv: 2,323 real arXiv charts spanning 8 subjects, every chart hand-picked, every question/answer human-written and verified; two task families (descriptive: title/labels/ticks/layout; reasoning: cross-axis comparison, trends, approximations) plus deliberate "unanswerable" questions probing hallucination.
- **Evidence (approach).** Stress-test prior benchmarks → demonstrate inflation; then build CharXiv with strict diversity (sources from 8 fields, varied subplot layouts, free-form short answers gradeable by LLM judge); explicit disentangling of perception vs reasoning.
- **Experiments.** 13 open + 11 proprietary MLLMs. GPT-4o 47.1 reasoning / 84.5 descriptive; InternVL-Chat-V1.5 29.2/58.5; humans 80.5/92.1. The 17.9-pt reasoning gap dwarfs prior 0.58-pt gap on existing benchmarks.
- **Analysis.** Descriptive↔reasoning correlation reveals models that can read titles often still fail trends; unanswerable items expose strong-prior hallucination in open models; complex layouts and overlapping legends are dominant failure modes.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 2 | qualitative | hero | Multi-panel chart with descriptive, reasoning, unanswerable QA + 3 model answers. | Open-source models miss basic layout; all miss reasoning. |
| 3 | 5 | flow + samples | pipeline | Curation funnel from arXiv → 2,323 charts → manual QA writing. | End-to-end human curation pipeline guarantees quality. |
| 4 | 6 | data-stats | data-stats | Charts per subject, subplot count, question type distribution. | Visual diversity vs prior benchmarks (Tab 1 alongside). |
| 6 | 8 | bar chart | headline-results | Per-model descriptive vs reasoning accuracy with human bar. | 47.1 vs 29.2 vs 80.5 — large frontier–open–human gaps. |
| 8 | 9 | scatter | correlation | Per-model descriptive accuracy vs reasoning accuracy. | Strong but imperfect correlation; reasoning-deficit cluster. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow the "stress test prior bench" framing: pick existing CAD benches (Text2CAD, CAD-Recode), perturb prompts mildly, show open models collapse → motivates BenchCAD.
- Borrow descriptive↔reasoning split: in CAD, separate "primitive recognition" (count holes/extrudes from image) from "parametric reasoning" (predict exact dims) — same disentangling proves where models really fail.
- Borrow "unanswerable" probe: include CAD prompts where the requested feature is impossible/ambiguous; measure hallucination rate.
- Borrow human topline: hire 3 CAD engineers to solve a 200-sample subset → headline number "humans 92, GPT-4o 35".
- Contrast: CharXiv uses LLM-judge grading on short-form answers; we must use CadQuery exec + IoU because code grading is geometric, not textual.

## One-line citation
Wang et al., "CharXiv: Charting Gaps in Realistic Chart Understanding in Multimodal LLMs," NeurIPS 2024 Datasets & Benchmarks.
