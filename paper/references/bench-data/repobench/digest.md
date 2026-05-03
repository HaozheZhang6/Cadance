# repobench — RepoBench: Benchmarking Repository-Level Code Auto-Completion Systems

**Venue:** ICLR 2024 · **Year:** 2023 · **URL:** https://github.com/Leolty/repobench · **PDF:** raw.pdf

## TL;DR
Three-task (Retrieve / Complete / Pipeline) repository-level next-line completion benchmark for Python & Java built from freshly crawled post-cutoff GitHub repos to expose cross-file context limits.

## Storyline (5-piece)
- **Problem.** CodeXGLUE / PY150 / GitHub Java Corpus measure single-file next-line completion; real Copilot-style systems must retrieve cross-file snippets and handle very long prompts — no benchmark covers this end-to-end.
- **Contribution.** RepoBench: Python (1,075 repos) + Java (594 repos) crawled after Feb 2023 to dodge contamination, with three sub-tasks — RepoBench-R (snippet retrieval), RepoBench-C (in-file + cross-file completion), RepoBench-P (full pipeline) — plus three masking settings (XF-F first cross-file, XF-R random cross-file, IF in-file).
- **Evidence (approach).** Use tree-sitter to parse imports → snippet definitions; build prompts that concatenate path + cross-file snippets + in-file context (≤30 preceding lines); commit to live updates (v1.1 already out).
- **Experiments.** Evaluate retrieval methods (lexical, semantic) for -R; evaluate Codex / StarCoder / CodeLlama / DeepSeek-Coder etc. on -C and -P; report EM / Edit-Sim / Pass.
- **Analysis.** XF-F is the hardest setting (no prior usage to copy); ground-truth retrieval lifts -P significantly; long-context models (Claude-100k) help on the pipeline task; retrieval errors compound completion errors.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 4 | prompt construction | pipeline | Cross-file snippet + in-file context concatenation for next-line prediction | How a RepoBench-C prompt is assembled |
| 2 | 6 | data-stats table | data-stats | Repos/files/lines counts for train + test, Python and Java | Scale and split breakdown |
| 3 | 7 | results table | headline-results | EM / ES across models, languages, settings on RepoBench-C | Per-setting model comparison |
| 4 | 8 | results table | ablation | RepoBench-P pipeline numbers across retrieval × completion combos | Retrieval quality drives end-to-end accuracy |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Three coupled sub-tasks sharing a data pool. For CAD-code, mirror as feature-retrieval (find relevant existing parts/macros) + completion (next operation) + pipeline (retrieve-then-edit) on the same parametric corpus.
- **Borrow:** Crawl-after-cutoff strategy. While our parts are procedural, we can still time-stamp procedural seeds and version registry releases so we can evaluate post-release public models on a clean partition.
- **Borrow:** Three masking settings (first vs. random vs. in-file). For CAD-edit, define analogue: first-feature-in-family, random-feature, intra-feature dimension — different difficulty regimes.
- **Contrast:** Their cross-file context is text imports; our analogue is referenced sketches / shared parameters in an assembly. Frame BenchCAD-Edit as "find dependent feature first, edit in place".
- **Avoid:** Reporting only EM. RepoBench shows ES (edit-similarity) tells a different story; we should report IoU + topology-sim + dimension error, not just exact-program match.

## One-line citation
RepoBench [Liu et al., ICLR 2024] introduces a live three-task (retrieve / complete / pipeline) repo-level code-completion benchmark in Python and Java built from post-cutoff GitHub crawls, demonstrating that cross-file retrieval quality is the dominant bottleneck in end-to-end auto-completion accuracy.
