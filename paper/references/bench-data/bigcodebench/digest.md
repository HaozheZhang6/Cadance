# bigcodebench — BigCodeBench: Benchmarking Code Generation with Diverse Function Calls and Complex Instructions

**Venue:** ICLR 2025 · **Year:** 2024 · **URL:** https://bigcode-bench.github.io · **PDF:** raw.pdf

## TL;DR
1,140 Python tasks that force LLMs to compose 723 function calls from 139 libraries across 7 domains under complex docstring or NL instructions; best model (GPT-4o) hits only 60% Pass@1 vs. 97% human.

## Storyline (5-piece)
- **Problem.** HumanEval / MBPP test self-contained algorithmic stubs; real-world tasks need *diverse* tool/library composition and *complex* multi-step instructions, gaps no existing exec-grade benchmark covers.
- **Contribution.** BigCodeBench (1,140 tasks, 7 domains, 139 libs, 723 distinct calls, 5.6 tests/task, 99% branch coverage) plus a Complete (docstring) and Instruct (NL-only) variant; evaluation of 60 LLMs.
- **Evidence (approach).** 3-stage human–LLM construction: (1) GPT-4 data-synth from real seed APIs, (2) program refactor + test-case generation, (3) human curation/refinement with feedback loop; open-ended unit tests verify behavior, not surface form.
- **Experiments.** Pass@1 / Pass@5 on Complete + Instruct; calibrated Pass@1 (correlation 0.982 between variants); per-domain and per-library performance; refusal-rate analysis for over-aligned models.
- **Analysis.** Strong positive correlation with HumanEval(+) but with much lower absolute scores — bench is harder yet ranks consistently; some instruction-tuned LLMs refuse long prompts; tool-use weakness is the dominant failure mode.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | task schematic | hero | Annotated docstring with parameters/returns/raises and matching test class | What a single BigCodeBench task contains |
| 2 | 2 | construction pipeline | pipeline | Three-stage data-synth → refactor+test-gen → human curation | Human-LLM collaboration loop |
| 3 | 5 | domain/library breakdown | data-stats | Distribution of tasks across 7 domains and 139 libraries | Coverage spread (CV / NLP / data / web / sys / crypto / general) |
| 4 | 8 | grouped bars | headline-results | Pass@1 of 60 LLMs on Complete and Instruct variants | GPT-4o tops at ~60%, ~50%; large head-to-tail gap |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Two-prompt-style variants (Complete = docstring/spec, Instruct = NL-only) — for CAD we should include a structured-spec prompt and an NL prompt of the same part to expose instruction-following gaps.
- **Borrow:** Branch-coverage / multi-test-per-task discipline. Translate to CAD: per part, validate not just reconstruction IoU but also derived feature checks (hole count, fillet radius, bbox).
- **Borrow:** Quantify library / API breadth. Our analogue is the family registry — report number of operations and primitives per task, not just family count.
- **Contrast:** They lean heavily on human curation (1,140 tasks, expensive). Procedural CAD generation gets coverage and scale without manual labeling, but we should add a small expert-curated subset (~100 parts) to mirror their quality bar.
- **Avoid:** A single Pass@1 number — BigCodeBench shows refusal and over-alignment confound results. Report multiple metrics (IoU, exec-pass, refusal rate, per-difficulty bands).

## One-line citation
BigCodeBench [Zhuo et al., ICLR 2025] benchmarks 1,140 multi-library multi-step Python tasks against 60 LLMs, finding the best model reaches only 60% Pass@1 vs. 97% human — exposing that current LLMs cannot reliably compose function-call tools under complex instructions.
