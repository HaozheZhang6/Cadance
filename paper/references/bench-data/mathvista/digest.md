# mathvista — MathVista: Evaluating Mathematical Reasoning of Foundation Models in Visual Contexts

**Venue:** ICLR 2024 (Oral) · **Year:** 2024 · **URL:** https://mathvista.github.io · **PDF:** raw.pdf

## TL;DR
6,141-example multimodal math benchmark unifying 28 source datasets + 3 newly curated (IQTest/FunctionQA/PaperQA); GPT-4V tops at 49.9 %, still 10.4 pts below humans (60.3 %).

## Storyline (5-piece)
- **Problem.** Math-reasoning benchmarks are mostly text-only; existing multimodal sets cover only narrow slices (geometry, ChartQA), so visual mathematical reasoning of LMMs is not systematically studied.
- **Contribution.** A consolidated benchmark with task taxonomy (5 tasks × 7 reasoning types × 12 visual contexts), three new datasets filling logical / algebraic-plot / scientific-figure gaps, and a fine-grained metadata schema enabling per-skill diagnosis.
- **Evidence (approach).** Aggregate 9 MathQA + 19 VQA datasets (≤400 ex each) via heuristic + 3-annotator manual filtering (99.2 % agreement); split into testmini-1k and held-out test-5.1k; metadata auto-labels validated at 94.1 % set-equality.
- **Experiments.** 12 foundation models evaluated (3 LLMs, 2 augmented LLMs, 7 LMMs, GPT-4V manual). Pipeline = response-gen → LLM answer-extractor (>99.5 % accurate) → normalized accuracy.
- **Analysis.** GPT-4V leads on algebraic plots/tables (sometimes > human) but loses on geometry and complex figures; failure modes dominated by visual-perception errors and arithmetic slips; self-verification + self-consistency emerge in GPT-4V.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| fig02_hero | 2 | radar+grouped bars | hero | Per-skill / per-context accuracy vs human | Defines headline gap (best LMM 49.9 vs human 60.3). |
| fig04_taxonomy | 4 | annotated examples | taxonomy | IQTest, FunctionQA, PaperQA samples with metadata | Shows three new datasets and label fields (task/context/grade/math). |
| fig05_data-stats | 5 | table+pie | data-stats | Key statistics (Table 1) and source-dataset distribution | 6,141 ex; FQA 26.8 %, GPS 21.5 %, MWP 19.5 %, TQA 15.3 %, VQA 16.9 %. |
| fig07_headline-results | 7 | results table | headline-results | Per-task / per-skill accuracy across 12 models | GPT-4V 49.9, Bard 34.8, PoT-GPT-4 33.9, human 60.3. |
| fig08_failure-cases | 8 | qualitative QA pairs | failure-cases | Bard outputs with red-marked perception/calc errors | Concrete hallucination + arithmetic-error patterns. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow the **dual-axis taxonomy** (task × reasoning skill × visual context) — for CAD that maps to op-family × geometric-skill × view-type, enabling skill-diagnostic radars.
- Borrow the **LLM-based answer-extractor** pattern (validated >99 % accuracy) to normalize free-form CAD-code outputs before exact-match scoring.
- Borrow **testmini / held-out test split** with public testmini and hidden test labels via online judge to prevent contamination.
- Contrast: MathVista aggregates 28 prior sets; BenchCAD must justify why a synthetic-first pipeline is preferable (no licensing thicket, controllable difficulty).
- Avoid: collapsing all results into one ALL number; MathVista's per-skill breakdown is what makes the gap analysis useful.

## One-line citation
Lu, P. et al. "MathVista: Evaluating Mathematical Reasoning of Foundation Models in Visual Contexts." ICLR 2024 (Oral). arXiv:2310.02255.
