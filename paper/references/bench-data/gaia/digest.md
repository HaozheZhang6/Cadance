# gaia — GAIA: A Benchmark for General AI Assistants

**Venue:** ICLR 2024 · **Year:** 2024 · **URL:** https://openreview.net/forum?id=fibxvahvs3 · **PDF:** raw.pdf

## TL;DR
466 real-world questions conceptually trivial for humans (92%) yet brutal for tool-augmented GPT-4 (15%), evaluated by exact-match on a single factoid answer — flipping the "harder than humans" benchmark trend toward proof-of-work assistant tasks.

## Storyline (5-piece)
- **Problem.**
  - Benchmarks saturate at increasing speed (GLUE, MMLU, GSM8k all near-solved).
  - Field's response — chase ever-harder-for-humans tasks (STEM, Law, USMLE) — fails because (i) overlap with pretraining → contamination, (ii) needs human or stronger-LLM judges that don't scale, (iii) prompt-sensitivity destabilizes scores.
  - For *general AI assistants* there is no benchmark that simultaneously requires reasoning + multimodality + tool use + web in one prompt.
- **Contribution.**
  - Reframes evaluation: tasks should be **easy for humans, hard for AIs** — analog of Proof of Work where solutions are hard to compute, easy to verify.
  - 466 hand-crafted questions across 3 difficulty levels (L1/L2/L3 by step + tool count), each with a single short factoid answer.
  - 166-question dev set released with annotations; 300 held out for the live leaderboard.
  - Construction guidelines (Appendix A) so the community can extend.
- **Evidence (approach).**
  - Each Q designed to need ≥1 of: web browsing (355/466), coding (154), multimodality (138), file-handling (129).
  - Answers absent in plain text from public web ⇒ memorization-resistant; reasoning trace stays inspectable.
  - Evaluation is automated quasi-exact-match against normalized GT (string / number / list).
  - System prompt enforces `FINAL ANSWER:` template; works zero-shot for any GPT-4-class model.
- **Experiments.**
  - GPT-4 (no plugins) 6.7%, GPT-4 + plugins (oracle, human-picked) 14.6%, GPT-4 Turbo, AutoGPT-4 4.0%, search engine 6.6%, **humans 92%**.
  - Difficulty validated: monotone score drop L1 → L2 → L3 across all systems.
  - Time-to-answer rises with level (humans 6→17 min); LLMs faster but rarely correct beyond L1.
- **Analysis.**
  - Plugin store churn means GPT-4+plugins is an upper-bound oracle, not reproducible.
  - Observes long plan execution + query refinement + backtracking in GPT-4+plugins traces.
  - Failures cluster on web-tool brittleness, file-reading, instruction-following.
  - Argues GAIA-success = "competent General AI" milestone (Morris et al. 2023 framework).

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig02 | 2 | Sample | hero | Three-tier example questions (L1/L2/L3) with ground-truth answers | Concretely defines GAIA tasks; sells the "easy-for-humans" framing in the first page |
| fig06 | 6 | Bar+scatter | data-stats | Capability coverage histogram + steps-vs-tools scatter colored by level | Shows breadth (web/code/multimodal) and validates the difficulty axis |
| fig07 | 7 | Bar | headline-results | Score and time-to-answer per method × level | The core "humans 92% vs LLM 15%" gap — the paper's punchline |
| fig08 | 8 | Bar | human-vs-model | Per-capability score breakdown at Level 1 | *Which* abilities models lack — diagnostic, not just aggregate |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Lead with the gap, not the dataset.**
  - GAIA's abstract opens with "92% vs 15%" before describing construction.
  - BenchCAD should foreground a single shocking human-vs-model headline on page 1 (e.g. "CAD designers 95% IoU≥0.99 vs frontier LM 12%").
- **Three-tier difficulty with concrete exemplars.**
  - L1/L2/L3 with a worked sample each sets intuition *before* any aggregate stat.
  - Mirror with easy/medium/hard CAD prompts beside their GT renders + dimension annotations.
- **Frame contribution as a philosophy shift, not just data.**
  - GAIA argues *against* "harder for humans" trend.
  - BenchCAD can argue *against* benchmarks scoring CAD via text similarity vs geometric equivalence — make this an explicit thesis paragraph in §1.
- **Hold out a private split + leaderboard from day 1.**
  - GAIA releases 166 dev / 300 hidden — standard for credibility against contamination.
  - Bake into our release plan; never publish the full hidden GT.
- **Keep headline scoring trivial.**
  - GAIA's eval = 1 regex + normalization.
  - BenchCAD: a single deterministic geometric check (IoU ≥ τ) as headline; defer richer analysis (chamfer-distance, topology, parametric agreement) to appendix.
- **Codify a construction guideline appendix.**
  - GAIA Appendix A teaches the community to extend the bench. We should ship a "How to write a BenchCAD prompt" appendix so the dataset is forkable.

## One-line citation
Mialon et al., "GAIA: A Benchmark for General AI Assistants," ICLR 2024.
