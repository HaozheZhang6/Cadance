# agentboard — AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://openreview.net/forum?id=z71F35iSiF · **PDF:** raw.pdf

## TL;DR
Replaces success-rate-only agent eval with a fine-grained **progress-rate** metric over annotated subgoals on 9 partially-observable multi-turn tasks, plus an open analytical web panel — turning binary failures into measurable progress.

## Storyline (5-piece)
- **Problem.** Agent benches collapse multi-turn behavior into a single success bit. In hard environments most models score ~0%, hiding meaningful differences. Existing benches also lack partial observability and unified multi-turn handling.
- **Contribution.** AgentBoard = (i) 9 tasks / 1013 environments unified under partially-observable multi-turn protocol (Embodied: AlfWorld, ScienceWorld, BabyAI; Game: Jericho, PDDL; Web: WebShop, WebArena; Tool: Query, Operation), (ii) **progress-rate metric** via human-annotated subgoals, (iii) open-source analytical board: sub-skill radar, hard/easy split, long-range-step curves, grounding/planning/memory/world-modeling/self-reflection breakdowns.
- **Evidence (approach).** Subgoal annotation methodology defined per task; progress = fraction of subgoals reached; success rate retained as special case. Web panel exposes per-skill scores and trajectory replay.
- **Experiments.** GPT-4 leads (~50 progress, ~25 success); Claude-2 / GPT-3.5-Turbo trail. Crucially, on Hard split where success rate is ~0, progress rate still discriminates (e.g. GPT-4 > Claude-2 by ~10 progress points).
- **Analysis.** Decomposes capability gaps into 6 sub-skills (planning, self-reflection, world modeling, memory, spatial nav, grounding) — radar shows GPT-4 dominates planning/grounding but lags on memory + self-reflection. Scaling step count reveals reasoning collapse.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig01 | 1 | Combined schematic | hero | Task suite + analytical panel mock + progress vs success curves | The whole pitch in one figure: bench + metric + tooling |
| fig04 | 4 | Pipeline | taxonomy | 9 tasks across Embodied/Game/Web/Tool with subgoal annotation example | Coverage and the unique subgoal-annotation contribution |
| fig06 | 6 | Bar | headline-results | Progress vs success rate per model across all tasks | Demonstrates the metric's value: discrimination where success≈0 |
| fig09 | 9 | Radar | radar-comparison | 6-dimensional sub-skill radar across leading models | Diagnostic: which capability each model lacks |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Invent a partial-credit metric to escape 0%-floor.** AgentBoard's biggest move: progress-rate instead of binary. For BenchCAD: don't only report IoU≥0.99 pass-rate; report continuous IoU, partial-feature-match, sketch-stage success — keeps the bench informative even when no model "passes."
- **Open analytical web panel as a deliverable.** Shipping a Streamlit/web tool is unusual for a D&B paper and gives the work a long tail of citations. We already have Synth Monitor — frame it as a first-class artifact.
- **Sub-skill decomposition radar.** Define 5-7 CAD competency axes (sketch correctness, dimensions, boolean topology, pattern symmetry, fillet/chamfer detail). Score each separately so the radar tells a story per model.
- **Hard/Easy split with separate curves.** AgentBoard reports both. BenchCAD: stratify by family complexity and report per-stratum so reviewers can't dismiss the bench as "just easy stuff."
- **Lead with the metric reform, not the dataset.** The paper's identity is "progress rate," not "9 tasks." Pick *one* methodological hook for BenchCAD beyond the data itself.

## One-line citation
Ma et al., "AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents," NeurIPS 2024 D&B.
