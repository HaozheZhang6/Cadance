# webarena_verified — WebArena Verified: Reliable Web-Agent Evaluation

**Venue:** NeurIPS 2025 SEA Workshop (OpenReview 2025) · **Year:** 2025 · **URL:** https://openreview.net/forum?id=webarena-verified · **PDF:** raw.pdf

## TL;DR
Audits all 812 WebArena tasks, fixes 257 (46 misaligned references + 211 ambiguous), replaces brittle string-match with type-aware backend-state checks + JSON schema, and ships a 137-task **Hard** subset that cuts cost 83% with no rank reversals.

## Storyline (5-piece)
- **Problem.** WebArena is the de-facto web-agent bench, but its eval is brittle: permissive substring matching, underspecified goals, no confidence intervals, "N/A" conflated with abandonment. Inflates scores 1.4-5.2%; even *empty-output* agents pass impossible tasks. Agent benchmarks need the SWE-bench-Verified treatment.
- **Contribution.** Four deliverables: (1) systematic ABC-framework audit of all 812 tasks with 4-annotator double-coding (Cohen's κ=0.83); (2) repaired tasks (46 reference-aligned + 211 disambiguated); (3) deterministic eval — type/normalization-aware comparators + REST/DB state checks + JSON schema with explicit status codes; (4) **WebArena Verified Hard**, 137-task subset preserving rank fidelity at 17% cost.
- **Evidence (approach).** Audit protocol combines automated detector + 7-agent trajectory analysis (top-10 leaderboard agents) + double-blind human annotation. Issue taxonomy: Reference Alignment (46), Task Ambiguity (211), Permissive String Matching (340), Context-Free Eval (92), Unachievable (36), Invariant Violations (812), Reporting (812).
- **Experiments.** OpenAI Operator baseline: verified scoring reduces false positives; Hard subset reduces false-negatives by ~11%. Macro-average over templates with 95% bootstrap CIs; parse-failure rate before/after schema; auto-recovery stats.
- **Analysis.** Drop-in compatible — agents only need JSON output. Hard subset selected by stratified sampling across intent templates, retains 100% multi-site tasks. Quantifies residual failure modes (nonconforming JSON, contradictory fields).

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig04 | 4 | Table | taxonomy | Issue categories × task counts with concrete bug examples | The audit's diagnostic core — names every failure mode |
| fig05 | 5 | Schematic | failure-cases | Permissive string match / context-free eval examples | Concrete bugs the reader can immediately see and believe |
| fig07 | 7 | Diagram | pipeline | Old vs new evaluator: substring → type-aware + state check + schema | Methodology contribution visualized |
| fig08 | 8 | Table | headline-results | Verified vs original scores per agent + Hard subset cost/quality | The payoff: cleaner scores, cheaper eval, ranks preserved |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Position as a *reliability* contribution, not just data.** The "Verified" framing is now a recognized genre (SWE-bench-V, OSWorld-V, τ-bench-V). If BenchCAD audits prior CAD benches (Text2CAD, GenCAD), frame it as "BenchCAD-Verified-style" rigor — instant credibility.
- **Issue taxonomy as a numbered table.** Don't just say "we cleaned data" — enumerate issue types with counts and exemplars (Table 1 here). Quantifies effort and exposes prior-work flaws politely.
- **Replace brittle metrics with deterministic structured eval.** They swap string-match for state-check + JSON schema. BenchCAD analog: replace text-similarity with geometric IoU + topology check + structured CQ-AST diff. Mention parse-failure rates before/after.
- **Cheap-and-Hard subset for adoption.** WebArena Verified Hard: 17% of tasks, same ranking, 11% lower FN. We should ship a `BenchCAD-Mini` (e.g. 100-200 prompts) for fast iteration with provable rank preservation vs the full set.
- **Macro-average + 95% CIs as default.** Forces the field to report uncertainty. Mandatory in our results tables.
- **Annotator agreement (Cohen κ) as a credibility number.** κ=0.83 with bootstrap CI is a small detail that signals professionalism.

## One-line citation
El Hattami et al., "WebArena Verified: Reliable Web-Agent Evaluation," NeurIPS 2025 SEA Workshop.
