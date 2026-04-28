# codesense — CodeSense: A Real-World Benchmark and Dataset for Code Semantic Reasoning

**Venue:** ICLR · **Year:** 2026 · **URL:** https://arxiv.org/abs/2506.00750 · **PDF:** raw.pdf

## TL;DR
First fine-grained semantic-reasoning benchmark built from **real Python/C/Java repos** with execution traces, exposing that even SOTA code LLMs do well on input/output prediction but collapse on variable-trace, branch-condition, and loop-invariant reasoning.

## Storyline (5-piece)
- **Problem.** HumanEval+, LiveCodeBench, etc. focus on coarse code generation or I/O prediction with synthetic/educational data. Real SE tasks (vuln detection, fault localization, invariant inference) need execution-oriented reasoning that current benches don't measure.
- **Contribution.** (i) **CodeSense dataset**: real-world Python/C/Java repo functions with paired execution traces (variable values per step, branch decisions, control-flow paths); (ii) **fine-grained reasoning task spectrum**: input generation under branch constraints, variable-value tracing, loop-invariant inference, control-flow path enumeration, vulnerability-pair location; (iii) **execution tracing framework + tool set** to construct ground truth at scale; (iv) baseline numbers on SOTA LLMs across all tasks.
- **Evidence (approach).** Collected real repos with executable test suites; instrumented them to dump per-step traces; auto-derived ground-truth answers for each fine-grained task from the trace. CoT and ICL prompting tested as model aids.
- **Experiments.** Evaluated GPT-4o, Claude-3.5, DeepSeek-Coder, Llama-3.1, etc. across all tasks per language. Headline: clear gap between coarse I/O prediction (~50–70%) and fine-grained tasks (often <30%).
- **Analysis.** CoT helps weakly; ICL helps when the example is structurally similar to the test, otherwise hurts. The authors argue the bottleneck is *operational semantics understanding*, not prompting — which can't be patched with more CoT tokens.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | Two code snippets (test-input gen + memory leak) annotated with semantic reasoning needed | Why fine-grained semantics matter for SE |
| 2 | 3 | tree | taxonomy | Task spectrum: input/output, variable trace, branch, control flow, vulnerability | Decomposition of "semantic reasoning" |
| 3 | 5 | diagram | pipeline | Repo→tests→trace instrumentation→GT extraction | How GT is auto-built from execution |
| 4 | 7 | bar/table | headline-results | Per-task accuracy across SOTA LLMs | Coarse-vs-fine performance gap |
| 5 | 9 | examples | failure-cases | Wrong CoT traces by GPT-4o on loop invariants | Concrete failure of "semantic" reasoning |

## Takeaways for BenchCAD
- **Real-repo grounding > synthetic** is becoming the D&B norm — we already do this with Fusion360 + DeepCAD-derived data, lean on it.
- **Trace-as-GT** is a powerful template for our "exec-pass + IoU" eval: don't just check final mesh, also instrument intermediate WP states (sketch closes, extrude bbox, etc.) for fine-grained scoring.
- **Coarse-vs-fine task spectrum** is a clean storytelling axis we can mirror: "code-runs" vs "geometry matches" vs "operation order matches" vs "named features present" — gives 4 sub-scores instead of one IoU.
- **Borrow** the framing that prompting (CoT/ICL) can't fix the underlying gap — strengthens the case for a post-training benchmark.

## One-line citation
Cui et al. (2025). CodeSense: A Real-World Benchmark and Dataset for Code Semantic Reasoning. ICLR 2026.
