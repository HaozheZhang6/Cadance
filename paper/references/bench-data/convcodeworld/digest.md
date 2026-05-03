# convcodeworld — ConvCodeWorld: Benchmarking Conversational Code Generation in Reproducible Feedback Environments

**Venue:** ICLR · **Year:** 2025 · **URL:** https://proceedings.iclr.cc/paper_files/paper/2025/file/6091f2bb355e960600f62566ac0e2862-Paper-Conference.pdf · **PDF:** raw.pdf

## TL;DR
Multi-turn code-gen benchmark with 9 reproducible feedback scenarios (3 compilation × execution-coverage × verbal-feedback combos) using simulated humans (GPT-4o at 1.5% the cost), plus an offline static "ConvCodeBench" that strongly correlates with full env runs.

## Storyline (5-piece)
- **Problem.** Real-world coding is multi-turn (run → fail → fix), but HumanEval/MBPP/BigCodeBench are single-turn. Existing multi-turn evals either need expensive human-in-the-loop or aren't reproducible.
- **Contribution.** (i) **ConvCodeWorld** env: 9 scenarios = {compilation, execution[partial cov, full cov], verbal[novice, expert]} crossed; (ii) **ConvCodeBench**: cheap static log-replay variant strongly correlated with the live env (Spearman ~0.95); (iii) systematic study showing models good at fewer turns (high MRR) aren't necessarily good at total solve rate (high Recall) — distinct axes.
- **Evidence (approach).** Simulated humans = GPT-4o generating verbal responses based on partial info ("novice" = vague hint; "expert" = code-specific suggestion). Cost: 1.5% of human annotation per dialog. ConvCodeBench reuses logged trajectories so replays are deterministic.
- **Experiments.** 17 LLMs (GPT-4, Claude, DeepSeek, Llama, etc.) across all 9 scenarios. Reports MRR (turns-to-solve) and Recall@N. Verifies ConvCodeBench↔ConvCodeWorld correlation.
- **Analysis.** Coverage feedback (full > partial > none) consistently helps; verbal-novice helps less than verbal-expert (confirmed). Some LLMs over-fit to "compile & try" and ignore verbal feedback — show up as flat MRR but rising Recall.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | diagram | hero | Two-panel: ConvCodeWorld env (live) vs ConvCodeBench (static replay) | The dual env / proxy design |
| 2 | 3 | diagram | pipeline | 3×3 feedback grid (compile / exec-cov / verbal-level) | 9 scenarios as orthogonal axes |
| 3 | 5 | bar/table | data-stats | Per-scenario eval-set composition + cost-vs-quality of GPT-4o sim | Cost-effectiveness justification |
| 4 | 7 | bar | headline-results | MRR + Recall across 17 LLMs in 9 scenarios | Headline solve rates |
| 5 | 9 | scatter | correlation | ConvCodeBench score vs ConvCodeWorld score per LLM | Tight correlation justifies cheap proxy |

## Takeaways for BenchCAD
- **Live + static-proxy** is a reviewer-friendly cost defense — we can offer a cached replay version for reproducibility (1k-task subset).
- **Feedback axes as a grid** (compile / render / verbal) is a great recipe for our paper: define our "feedback types" cleanly so reviewers can see the eval design upfront.
- **Two-axis metric** (turns-to-solve vs total-solved) prevents oversell — we should similarly split exec-pass-rate from CD-quality.
- **Borrow** the cost-of-eval transparency table — explicitly state "1.4k subset costs $X to run, full 17.8k costs $Y" lowers reviewer adoption friction.
- **Avoid** over-promising on simulated-human verbal feedback — model-judges have known calibration issues (see infinity_chat); use only for limited dimensions.

## One-line citation
Han et al. (2025). ConvCodeWorld: Benchmarking Conversational Code Generation in Reproducible Feedback Environments. ICLR 2025.
