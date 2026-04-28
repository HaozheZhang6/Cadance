# agentbench — AgentBench: Evaluating LLMs as Agents

**Venue:** ICLR 2024 · **Year:** 2024 · **URL:** https://openreview.net/forum?id=zAdUB0aCTQ · **PDF:** raw.pdf

## TL;DR
First multi-environment LLM-agent benchmark spanning 8 interactive worlds (OS, DB, KG, web shop, web browse, card game, lateral thinking, household), evaluates 29 LLMs and exposes a yawning API-vs-OSS gap (4.5×).

## Storyline (5-piece)
- **Problem.**
  - LLM-as-agent claims (AutoGPT, BabyAGI, AgentGPT) outpace rigorous evaluation.
  - Prior agent benches are single-environment text games (closed action space), embodied/GUI multimodal simulators (don't fit text-only LLMs), or repurposed static QA (doesn't test interaction).
  - No systematic, text-only, multi-domain agent testbed exists, so cross-model comparison is impossible.
- **Contribution.**
  - **AgentBench**: 8 distinct environments grouped under 3 groundings:
    - *Code* — Operating System (bash), Database (MySQL), Knowledge Graph (Freebase APIs).
    - *Game* — Digital Card Game (Aquawar), Lateral Thinking Puzzles, House-Holding (ALFWorld).
    - *Web* — Web Shopping (WebShop), Web Browsing (Mind2Web).
  - 5 of 8 environments are net-new; the other 3 are reformatted classics.
  - Unified HTTP-based evaluation toolkit so any text LLM (API or OSS) can be plugged in with one client.
- **Evidence (approach).**
  - Every env reformulated as a multi-turn interactive trajectory; the agent emits text actions, env returns text observations.
  - Per-env metric normalized to a comparable scale; weighted overall score reported as a single headline number.
  - Existing benches (ALFWorld, WebShop) wrapped in the same protocol → no separate adapters needed downstream.
- **Experiments.**
  - 29 LLMs evaluated: API tier (GPT-4, Claude-3-Opus, Claude-2/instant, GLM-4, GPT-3.5-Turbo, text-davinci-002/003, Bison) + OSS tier (CodeLlama-34B, Llama-2-13B/70B, Vicuna-13B, ChatGLM-6B, Dolly-12B, OpenAssistant-12B).
  - GPT-4 overall 4.01, Claude-3 3.11, GLM-4 2.89, top OSS ~1.0; **API avg 2.32 vs OSS avg 0.51** ⇒ ≈4.5× gap.
- **Analysis.**
  - Failure modes diagnosed: poor long-horizon reasoning, decision drift, instruction-violation, hallucinated tool syntax.
  - Code-training has **ambivalent** effect — helps OS/DB, sometimes *hurts* game and lateral-thinking tasks.
  - Two levers identified: high-quality multi-turn alignment data + instruction-following capability.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig01 | 1 | Radar + bar | radar-comparison | Per-env relative score radar + overall ranking bar | Hero image: ranks all models, shows OSS-API chasm at a glance |
| fig02 | 2 | Schematic | taxonomy | 8 environments grouped by Code/Game/Web grounding with prompt examples | Sells the breadth/coverage claim with concrete task examples |
| fig07 | 7 | Table | headline-results | Detailed per-environment scores for 29 LLMs | Full leaderboard — primary deliverable |
| fig08 | 8 | Table | data-stats | Dataset sizes, weights, train/test splits per environment | Methodology depth — shows the engineering investment |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Radar chart for multi-axis benches.**
  - AgentBench's Fig 1 radar (per-env relative-to-best) is the most-copied template in agent papers.
  - BenchCAD should radar across CAD families/difficulties so a model's lopsided strengths and blind spots show in one glance.
- **3-grouping taxonomy upfront.**
  - Code / Game / Web gives readers a memorable structure *before* any numbers.
  - Mirror with e.g. *Primitive / Composite / Parametric* or *Sketch / Solid / Pattern* — keep it to ≤3 buckets so the radar stays legible.
- **Lead with the gap framing, not the leaderboard.**
  - They turn a leaderboard into a *finding* ("4.5× API-vs-OSS gap").
  - BenchCAD: frame results as "code-LM vs vision-LM gap" or "specialized-CAD vs general-LM gap" — a single sticky number.
- **Reformulate existing data into one protocol.**
  - Wrapping ALFWorld/WebShop in a uniform harness widens reach without reinventing.
  - We can wrap Fusion360 + DeepCAD + synthetic under one CadQuery-eval API so all prior data feeds the same metric pipeline.
- **Diagnostic findings as 1-line takeaways.**
  - "Code training is ambivalent" / "instruction following is the bottleneck" are quotable.
  - Reserve a "What we learned about CAD-LMs" subsection with 3-5 such crisp claims.
- **Engineering investment as legitimacy signal.**
  - Their Table for per-env stats + weights signals depth of effort. Borrow.

## One-line citation
Liu et al., "AgentBench: Evaluating LLMs as Agents," ICLR 2024.
