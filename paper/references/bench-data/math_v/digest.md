# math_v — Measuring Multimodal Mathematical Reasoning with the MATH-Vision Dataset

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://mathllm.github.io/mathvision/ · **PDF:** raw.pdf

## TL;DR
3,040 expert-curated math-competition problems (16 subjects × 5 difficulty levels) reveal a 38-point human–LMM gap (humans 68.8 vs best LMM 30.4), exposing geometry/topology blind spots hidden by inflated MathVista scores.

## Storyline (5-piece)
- **Problem.** On MathVista, GPT-4o 63.8 surpasses humans 60.3 — yet authors show LMMs fail elementary problems trivial for kids; existing benches concentrate on plane geometry + recognition templates.
- **Contribution.** MATH-Vision (MATH-V): 3,040 problems from 19 real math olympiads/competitions, 16 disciplines including 8 newly introduced (descriptive geometry, graph theory, topology, transformation geometry, solid geometry, etc.), graded across 5 difficulty levels; 1,532 open-ended + 1,508 multiple-choice.
- **Evidence (approach).** Holistic collection (problem image + statement together, no annotator-written templates), expert cross-validation, difficulty calibration by competition grade band; explicit subject taxonomy verified by experts.
- **Experiments.** Evaluate Gemini-1.5-Pro, GPT-4o, GPT-4-turbo, InternVL-1.2-Plus, plus open models. Best LMM (GPT-4o) 30.4 vs random 7.2 vs human 68.8; MathVista podium (Gemini 63.9, GPT-4o 63.8) collapses on MATH-V.
- **Analysis.** Per-subject radar shows worst categories are transformation geometry, descriptive geometry, topology, graph theory; per-difficulty curves show models fall off cliff at L3+; error analysis groups errors into vision (mis-reading), reasoning, calculation, knowledge, and rejection.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 1 | radar + samples | hero | Per-subject zero-shot accuracy radar + 3 trivially-easy items LMMs fail. | Demonstrates Gemini/GPT-4o below human on most subjects. |
| 2 | 4 | wheel | taxonomy | 16-subject pie chart with example problems per subject. | Shows breadth/balance, highlights newly-introduced classes. |
| 4 | 5 | table | headline-results | Accuracy per model × subject including open models. | Headline numbers: human 68.8, GPT-4o 30.4. |
| 5 | 6 | line chart | difficulty | Accuracy vs difficulty level (1–5) per model. | Sharp performance cliff at L3+; humans degrade gracefully. |
| 6 | 7 | qualitative | failure-cases | Error breakdown across vision/reasoning/calc/knowledge categories. | Reasoning errors dominate; vision errors >20% on geometry. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow taxonomy-by-discipline: enumerate 16 CAD families/disciplines (extrude, revolve, shell, sweep, loft, pattern, …) and report per-family scores — radar plot becomes signature figure.
- Borrow difficulty grading 1–5 and show the "difficulty cliff" curve; reviewers find this sticky.
- Borrow human-trivial-LMM-fail anecdotes: handpick 3 dead-simple parts (single cylinder, drilled cube, L-bracket) on which all LMs miss the dimension — direct narrative weapon.
- Borrow error taxonomy (vision/reasoning/calc/knowledge → for us: vision/topology/parametric/syntax/exec) for per-prediction tagging.
- Avoid: MATH-V uses MCQ for half the data — we should not, since CAD code is generative; but borrow their open-ended grading via numeric tolerance.

## One-line citation
Wang et al., "Measuring Multimodal Mathematical Reasoning with the MATH-Vision Dataset," NeurIPS 2024 Datasets & Benchmarks.
