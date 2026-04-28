# gpqa — GPQA: A Graduate-Level Google-Proof Q&A Benchmark

**Venue:** COLM 2024 · **Year:** 2024 · **URL:** https://openreview.net/forum?id=Ti67584b98 · **PDF:** raw.pdf

## TL;DR
448 PhD-expert-written biology / physics / chemistry MCQs where domain experts hit 65% (74% post-correction), highly-skilled Google-armed non-experts only 34% — built explicitly as a scalable-oversight testbed for *superhuman* models.

## Storyline (5-piece)
- **Problem.** As LLMs approach the frontier of human knowledge, RLHF-style oversight requires testbeds where (i) ground truth exists, (ii) experts know it, (iii) skilled non-experts *cannot* recover it even with the open web and 30+ minutes. Existing benches don't satisfy this — they're either solvable by Google or lack rigorous expert validation.
- **Contribution.** GPQA: 448 graduate-level MCQs (biology, physics, chemistry sub-domains) with a multi-stage human pipeline: writer → expert validator #1 + revision → expert validator #2 → 3 non-expert validators (~37min, web allowed) → labeled set + DIAMOND subset (≥2 experts agree, ≤1 non-expert correct).
- **Evidence (approach).** Detailed annotation protocol with calibration; post-hoc agreement metric; explicit handling of "expert mistakes vs genuine disagreement"; canary string embedded against future training-corpus contamination. Two splits: full (448), DIAMOND (198 hardest).
- **Experiments.** Experts 65% (74% adjusted); non-experts 34%; GPT-4 39% (Nov 2023) → Claude-3 Opus ~60% (Mar 2024). Documents rapid SOTA progression on a bench designed to stay hard.
- **Analysis.** Quantifies "Google-proofness" via non-expert score floor; discusses scalable-oversight implications — the bench is meant to enable empirical study of debate/IDA-style protocols on questions humans can't solve unaided. Releases bench *with* request not to plain-text-reveal items, plus canary string.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| fig02 | 2 | Pipeline | pipeline | Question writing → 2 expert validators → 3 non-expert validators → DIAMOND filter | The annotation cookbook — the paper's main methodological artifact |
| fig04 | 4 | Stats table | data-stats | Domain breakdown (Biology/Physics/Chemistry sub-fields), counts | Composition + breadth |
| fig06 | 6 | Bar | human-vs-model | Expert vs non-expert vs GPT-4 vs other models per domain | The headline gap — Google-proof claim quantified |
| fig07 | 7 | Bar | headline-results | Model accuracy across full + DIAMOND splits over time | Discriminability + room-for-improvement |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B paper)
- **Multi-stage expert annotation pipeline is the credibility centerpiece.** GPQA spends most of §3 on the pipeline, not the dataset. BenchCAD should make its CAD-engineer review process equally explicit (designer writes → engineer #1 verifies geometry → engineer #2 cross-checks → non-expert tries to reproduce from prompt).
- **Define a "X-proof" framing.** "Google-proof" is the paper's most quotable phrase. BenchCAD analog: "**retrieval-proof**" (no near-duplicates in CAD-Recode/Text2CAD training) or "**template-proof**" (cannot be solved by program-synthesis lookup).
- **Ship a smaller "DIAMOND" hardest subset alongside the full set.** Echoes WebArena Verified Hard. We should ship `BenchCAD-Diamond` of 100-200 prompts where current frontier models score <50%.
- **Quantify validator effort.** "37 minutes average, web allowed" makes the difficulty *concrete*. BenchCAD: report median time a CAD-trained student takes to solve a hard prompt manually.
- **Embed canary string + contamination-awareness clause.** Standard practice now for benches likely to be valuable for years. We should embed a canary in every CAD prompt.
- **Frame the bench around a *future* research question, not the present.** GPQA is justified as a scalable-oversight testbed — it gives the dataset purpose beyond leaderboard chasing. BenchCAD should anchor to a meta-question: e.g. "can a model invent a parametric design from intent?"

## One-line citation
Rein et al., "GPQA: A Graduate-Level Google-Proof Q&A Benchmark," COLM 2024.
