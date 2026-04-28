# swebench_pro — SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?

**Venue:** OpenReview 2025 (under review) · **Year:** 2025 · **URL:** https://openreview.net/forum?id=SWEBenchPro · **PDF:** raw.pdf

## TL;DR
1,865 long-horizon SWE issues from 41 GPL/commercial repos with 100+ line multi-file patches; even GPT-5 solves only 25.9% Pass@1, exposing the gap between SWE-Bench-Verified saturation and real enterprise work.

## Storyline (5-piece)
- **Problem.** SWE-Bench Verified is approaching saturation, dominated by trivial 1–10 line patches; permissive-license repos leak into pre-training, so contamination clouds existing scores.
- **Contribution.** SWE-Bench Pro: (1) public set (11 GPL repos), held-out set (12 repos), commercial set (18 startup repos with formal partnerships) — three contamination tiers; (2) tasks ≥10 LoC, avg 107.4 LoC across 4.1 files; (3) 3-stage human-in-the-loop verification; (4) trajectory-level failure-mode taxonomy.
- **Evidence (approach).** Source repos under copyleft (legal anti-leak) or proprietary; filter trivial patches; clarify ambiguous issues with human edits; recover unit tests as oracle while constraining solution space to avoid false negatives; standard scaffold for agent eval.
- **Experiments.** Evaluate widely used coding agents (Claude/GPT/Gemini/open-source) under one scaffold; report Pass@1 on public, held-out, and commercial sets; per-language and per-repo breakdowns.
- **Analysis.** GPT-5 = 25.9% best (public); held-out vs. public gap small → no overfit signal yet; failures dominated by wrong-localization and incomplete patches; commercial set hardest.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 4 | curation pipeline | pipeline | Repo selection → issue mining → human verification → test recovery | Three-stage human-in-the-loop workflow |
| 2 | 5 | repo / language stats | data-stats | 41 repos × language × LoC / files-per-patch distributions | Multi-file long-horizon nature of tasks |
| 3 | 7 | grouped bars | headline-results | Pass@1 of agents on public / held-out / commercial sets | GPT-5 25.9%; sub-25% for everyone else |
| 4 | 9 | failure taxonomy | failure-cases | Clustered error categories from agent trajectories | Wrong-fix, wrong-file, incomplete-patch dominate |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Three-tier release (public / held-out / proprietary). For CAD, mirror as a public 1k subset, a held-out 1k for overfit checks, and an industry-collab subset of real product parts evaluated only via API.
- **Borrow:** Trajectory-level failure-mode clustering, not just a pass-rate number. We should cluster CAD-edit failures (wrong feature located, wrong dimension, broken topology) and report category mass.
- **Borrow:** Filter out "trivial" tasks. We should drop parts whose programs are <N operations to avoid trivial-skewed leaderboards, mirroring SWE-Pro's 10-LoC floor.
- **Contrast:** Their long-horizon = patch length & file count; ours = operation depth & cross-feature consistency. Make this analogy explicit so reviewers see we're tackling the same axis in a different domain.
- **Avoid:** Repo-level overfit. SWE-Pro caps at 100 instances/repo; we should cap parts/family or parts/seed to prevent any one geometry pattern dominating the score.

## One-line citation
SWE-Bench Pro [Anonymous, OpenReview 2025] curates 1,865 long-horizon enterprise SWE problems across public/held-out/commercial tiers with avg 107-LoC patches, where even GPT-5 reaches only 25.9% Pass@1, providing the contamination-resistant successor to a saturating SWE-Bench Verified.
