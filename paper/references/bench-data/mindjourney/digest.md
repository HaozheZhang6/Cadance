# mindjourney — MindJourney: Test-Time Scaling with World Models for Spatial Reasoning

**Venue:** NeurIPS 2025 · **Year:** 2025 · **URL:** https://umass-embodied-agi.github.io/MindJourney/ · **PDF:** raw.pdf

## TL;DR
Test-time scaling framework that pairs a frozen VLM with a controllable video-diffusion world model: VLM proposes camera trajectories, world model renders them, VLM picks helpful views; +7.7% avg on SAT spatial reasoning across four VLMs without any finetuning.

## Storyline (5-piece)
- **Problem.** SOTA VLMs treat images as static 2D and fail at perspective-shift / egocentric-motion questions; spatial benchmarks (SAT, SpatialRGPT, SPAR) consistently expose this.
- **Contribution.** MindJourney = VLM + world-model coupling at test time. Spatial Beam Search interleaves trajectory expansion (world model rolls out new view) with question-aware pruning (VLM scores exploration + helpfulness). Plus Search World Model (SWM), trained on Wan2.2-TI2V-5B + Habitat synth + RealEstate10K + DL3DV-10K.
- **Evidence (approach).** Action space = {forward d, turn-left θ, turn-right θ}; trajectories of length ≤n built into pose sequences fed to pose-conditioned video-diffusion world model. Beam search with width B, depth n, ≤k repeats per action; thresholds γ_exp, γ_help; evidence buffer of top-H helpful views fed to QA-VLM in single pass.
- **Experiments.** SAT benchmark (Real + Synthesized); 5 sub-tasks: EgoMovement, ObjectMovement, EgoAction, GoalAiming, Perspective. Backbones: GPT-4o, GPT-4.1, InternVL3-14B, OpenAI o1. Two world models: SWM (custom) + Stable-Virtual-Camera (SVC). GPT-4o 60.3→70.6 (+10.3); o1 74.6→84.7 on SAT-Real.
- **Analysis.** Method-agnostic across 4 VLMs and 2 world models; even compounds with o1's RL-based reasoning. Largest gains on ego-motion / perspective questions where world model directly supplies the missing 3D evidence.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 2 | 2 | concept fig | hero | World model imagines walk; VLM answers perspective query | One-glance pitch of test-time-with-world-model |
| 4 | 4 | pipeline overview | pipeline | Spatial Beam Search loop: expand → score → prune → answer | End-to-end algorithm |
| 5 | 5 | trajectory expansion | pipeline | k=3, d=0.25, θ=10° rolls 9 candidate views | Action-space expansion mechanics |
| 7 | 7 | SAT-Real table | headline-results | +MJ accuracy gains across 4 VLMs and 5 SAT subtasks | Method-agnostic improvement |
| 8 | 8 | SAT-Synthesized table | ablation | Same gains on synthetic SAT split | Generalization to in-distribution |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: test-time-scaling framing — BenchCAD evaluation should report VLM + tool-use augmentation (e.g., VLM + executor / VLM + retriever) alongside vanilla VLM, mirroring SAT's +MJ rows.
- Borrow: per-skill table (5 SAT sub-tasks) — directly maps to per-CAD-skill scoring (sketch / extrude / fillet / chamfer / loft).
- Contrast: MindJourney's evidence is generated; CAD bench's evidence is parametric ground-truth — opposite information flow but same evaluation grain.
- Borrow: include tool-augmented baseline (e.g., VLM + CadQuery REPL) as the spatial-beam-search analog; expect reviewers to ask if simple tool-use closes the gap.
- Avoid: claiming a method paper in a D&B submission — MindJourney is a method on existing SAT, BenchCAD must keep dataset-side novelty primary.

## One-line citation
Yang et al., "MindJourney: Test-Time Scaling with World Models for Spatial Reasoning," NeurIPS 2025.
