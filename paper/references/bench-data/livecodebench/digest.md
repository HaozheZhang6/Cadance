# livecodebench — LiveCodeBench: Holistic and Contamination-Free Evaluation of Large Language Models for Code

**Venue:** ICLR 2025 · **Year:** 2024 · **URL:** https://livecodebench.github.io · **PDF:** raw.pdf

## TL;DR
A continuously refreshed coding benchmark with date-tagged problems from LeetCode/AtCoder/Codeforces and four scenarios (gen, repair, exec, test-output) that exposes contamination by per-month performance drops after model cutoff dates.

## Storyline (5-piece)
- **Problem.** HumanEval / MBPP and even APPS / Code-Contests are saturated, lossy (multi-correct outputs, sparse tests), and contaminated; they only score generation, ignoring repair / execution / test-prediction.
- **Contribution.** LiveCodeBench: 600+ date-stamped problems (May 2023–Aug 2024), four holistic scenarios, 18+ tests/problem on average, evaluation against 50+ open and closed LLMs, plus an explicit "decontamination by date-window" methodology.
- **Evidence (approach).** Scrape LeetCode/AtCoder/Codeforces with release timestamps; filter for unambiguous I/O autograding; expand stress tests via a hidden generator; bundle into four scenarios sharing the same problem pool.
- **Experiments.** Bimonthly time-window Pass@1 for DeepSeek/GPT-4o/Claude-3 shows sharp post-cutoff drops; comparison with HumanEval(+) shows weaker correlation for older models; radial chart of Code Generation / Self-Repair / Test-Output / Execution per model.
- **Analysis.** Models that overfit HumanEval underperform on LCB; reasoning models (e.g. o-series) close the gap on harder LeetCode/CF tiers; self-repair gains plateau after one round; test-output prediction strongly correlates with code generation but is harder.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 2 | time-window line + radial | hero | Pass@1 by month and four-scenario radar across top models | Sharp post-cutoff drop; per-scenario differences |
| 2 | 5 | pipeline schematic | pipeline | Problem collection, test augmentation, four-scenario assembly | How LCB constructs each scenario from one pool |
| 3 | 7 | grouped bar charts | headline-results | Pass@1 per scenario across major LLM families | GPT-4 / Claude / DeepSeek leaderboard |
| 4 | 8 | scatter (HumanEval vs LCB) | correlation | Per-model HumanEval vs LCB performance | HE saturated; LCB still discriminates |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Multiple scenarios on a shared item pool — cad-gen / cad-edit / cad-repair / cad-QA from the same parametric parts gives holistic capability assessment without N separate datasets.
- **Borrow:** Date-stamping or version-stamping each part for contamination tracking; even synthetic CAD benefits from release windows for fair public-model evaluation.
- **Borrow:** Per-problem test multiplicity (LCB averages 18) — for CAD, sample multiple parameter realizations per family so a single "lucky" memorized solution cannot pass.
- **Contrast:** LCB depends on continuous human contest streams; we replace that with procedural family expansion — same anti-contamination outcome, no scraping fragility.
- **Avoid:** Treating one scenario as the leaderboard. LCB's radar shows each model has strengths/weaknesses; we should publish per-task rankings and a normalized aggregate, not a single number.

## One-line citation
LiveCodeBench [Jain et al., ICLR 2025] introduces date-tagged contamination-free coding problems across four holistic scenarios, demonstrating that time-window evaluation reveals dramatic post-cutoff Pass@1 drops invisible to static benchmarks like HumanEval.
