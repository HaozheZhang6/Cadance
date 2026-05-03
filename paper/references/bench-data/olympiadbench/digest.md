# olympiadbench — OlympiadBench: A Challenging Benchmark for Promoting AGI with Olympiad-Level Bilingual Multimodal Scientific Problems

**Venue:** ACL 2024 · **Year:** 2024 · **URL:** https://github.com/OpenBMB/OlympiadBench · **PDF:** raw.pdf

## TL;DR
8,952 olympiad-level bilingual (EN/ZH) math + physics problems with expert step-by-step solutions; best model GPT-4V scores 17.23 % overall (11.28 % physics).

## Storyline (5-piece)
- **Problem.** GSM8K / MATH are saturating (GPT-4 >97 % / 84 %); existing physics benchmarks are MCQ and easy; few benchmarks demand expert-level scientific reasoning, are bilingual, or combine math + physics with images.
- **Contribution.** Olympiad-caliber benchmark sourced from IMO/IPhO/Chinese olympiads/Gaokao; 57 % of problems carry images; every problem has expert annotated solution; five answer-type categories (Numeric / Expression / Equation / Tuple / Interval) enable automatic scoring.
- **Evidence (approach).** PDF→Mathpix OCR→manual cleanup→model-based dedup; manual labelling of subfield + question type; SymPy-driven scorer with type-specific equivalence checks (numeric tol 1e-8; symbolic subtraction-to-zero).
- **Experiments.** Zero-shot eval of 5 LMMs (GPT-4V, Gemini-Pro-V, Qwen-VL-Max, Yi-VL-34B, LLaVA-NeXT-34B) and DeepSeekMath-7B-RL; English/Chinese × competition/CEE splits; manual sampling check on theorem-proving subset.
- **Analysis.** Common failures = computational error, hallucinated reasoning, knowledge omissions, choosing complex over simple proofs; physics far harder than math; bilingual gap narrow.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| fig01_hero | 1 | annotated problem | hero | IMO number-theory problem with full expert solution | Sample illustrates open-ended free-form proof style and difficulty. |
| fig04_gap-vs-prior | 4 | comparison table | gap-vs-prior | Table 1 vs SciBench/MMMU/MathVista/AGIEval/MATH | OlympiadBench leads in size (8.9k), bilingual, multimodal, detailed solutions. |
| fig05_taxonomy | 5 | hierarchy diagram | taxonomy | Subfield breakdown of physics-COMP, math-COMP, math-CEE | 13 math-CEE topics; 4 math-COMP; 5 physics topics (Mech/EM/Thermo/Optics/Modern). |
| fig07_headline-results | 7 | main table | headline-results | Accuracy per language / source / subject / model | GPT-4V 17.23 avg; physics 11.28 %; open-source ≤4 %. |
| fig09_failure-cases | 9 | annotated GPT-4V trace | failure-cases | GPT-4V error categories with examples | Hallucinated reasoning, knowledge omission, logical fallacy. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow **answer-type schema** (Numeric/Expression/Equation/Tuple/Interval) → CAD analogue: dimension / equation / shape-list / sketch-tuple, each with a deterministic equivalence checker.
- Borrow **expert step-by-step solutions** → motivates including reference CadQuery code AND natural-language build rationale per problem.
- Borrow **bilingual axis** as inspiration: a small ZH/JA CAD-prompt slice would broaden community impact.
- Contrast: OlympiadBench is human-sourced and expensive; BenchCAD's synthetic generator yields >100k clean samples — own that as a scaling story while matching difficulty via stratified sampling.
- Avoid: theorem-proving scoring gap (manual sampling only) — design CAD geometric correctness so it stays fully automatic.

## One-line citation
He, C. et al. "OlympiadBench: A Challenging Benchmark for Promoting AGI with Olympiad-Level Bilingual Multimodal Scientific Problems." ACL 2024.
