# rigorous_agent_bench — Establishing Best Practices for Building Rigorous Agentic Benchmarks

**Venue:** NeurIPS 2025 D&B (OpenReview) · **Year:** 2025 · **URL:** https://openreview.net/forum?id=rigorous-agentic-benchmarks · **PDF:** raw.pdf

## TL;DR
Audits 10 popular agent benchmarks (SWE-bench-V, τ-bench, GAIA, WebArena, KernelBench, …) and shows up to 100% relative misestimation; distills the **Agentic Benchmark Checklist (ABC)** centered on *task validity* and *outcome validity*, then applies it to CVE-Bench to cut overestimation 33%.

## Storyline (5-piece)
- **Problem.** Agent benchmarks are everywhere but riddled with errors. Concrete examples opening the paper: SWE-bench-Verified has 24% top-50 leaderboard positions miscredited; τ-bench gives an empty-output agent 38% on intentionally impossible tasks; KernelBench overestimates kernels by 31%. The field is reporting unreliable numbers.
- **Contribution.** Distill agent-eval rigor into a 2-axis taxonomy:
  - **Task validity** — solvable ↔ has-target-capability (no shortcuts, no impossibles).
  - **Outcome validity** — task-success ↔ positive-eval-result (tests truly verify).
  Operationalize as the ABC checklist (concrete, actionable, item-by-item). Apply ABC to 10 benches; demonstrate fix on CVE-Bench (33% overestimation removed).
- **Evidence (approach).** Survey 17 benchmarks + prior pitfall papers; develop checklist via authors' building experience. Each ABC item is mapped to detection method + remediation. Conceptual diagram (Fig 1) splits eval into operational pipeline (agent→outcome→evaluator) vs conceptual mapping (capability ↔ success ↔ positive result).
- **Experiments.** 10 benches assessed: 7 fail outcome validity, 7 fail task validity, **all 10** fail reporting standards. New issues discovered: (i) SWE-Lancer 100% achievable without solving; (ii) KernelBench 31% inflation; (iii) WebArena 5.2% inflation from string-match.
- **Analysis.** Case study: ABC applied to CVE-Bench during development reduces overestimation 33% absolute, expert-confirmed. Argues benchmarks should ship a "validity card" disclosing residual issues.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig03 | 3 | Conceptual schematic | taxonomy | Operational vs conceptual eval; defines task validity + outcome validity | The paper's framework — readers cite this diagram |
| fig05 | 5 | Pipeline | pipeline | ABC checklist application flow with categorization | How to actually use the checklist |
| fig08 | 8 | Bar | headline-results | Misestimation magnitudes across 10 audited benchmarks | The "this is a real problem" evidence |
| fig09 | 9 | Case study | case-study | Before/after CVE-Bench scores under ABC remediation | Demonstrates checklist's practical impact |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Self-audit your bench against ABC and publish the report card.** The single most defensive move for a 2026 D&B submission is to include a "BenchCAD vs ABC" appendix where every checklist item is addressed. Reviewers will have read this paper.
- **Define BenchCAD's analogues of *task validity* + *outcome validity*.** Task validity for CAD: "is geometric output achievable from the prompt and *only* via real CAD reasoning, not template lookup?" Outcome validity: "does IoU≥τ truly mean shape-match, not coincidental bbox overlap?" State both explicitly.
- **Open with shocking miscalibration numbers from prior CAD benches.** This paper opens with "empty agent gets 38%". BenchCAD should open with e.g. "Text2CAD scores X% on Y eval, but with proper geometric check drops to Z%."
- **Ship a *checklist* artifact.** They abstract their lessons into ABC. We can ship a "CAD Bench Hygiene Checklist" (geometric vs textual eval, GT correctness, prompt-spec ambiguity, eval determinism, leaderboard hygiene). Adoption-driver.
- **Two-failure-mode framing > many.** Reducing complexity to 2 axes (task/outcome validity) is memorable. BenchCAD should similarly compress its critique to 2-3 named failure modes.
- **Case-study a single benchmark improvement quantitatively.** Show "without our methodology, X bench overstates by N%" — this is what makes a methodology paper sticky.

## One-line citation
Zhu et al., "Establishing Best Practices for Building Rigorous Agentic Benchmarks," NeurIPS 2025 D&B.
