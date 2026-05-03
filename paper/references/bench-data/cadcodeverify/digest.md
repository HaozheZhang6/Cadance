# cadcodeverify — Generating CAD Code with Vision-Language Models for 3D Designs (CADCodeVerify + CADPrompt)

**Venue:** ICLR · **Year:** 2025 · **URL:** https://arxiv.org/abs/2410.05340 · **PDF:** raw.pdf

## TL;DR
Alrashedy & Tambwekar et al. introduce CADPrompt — the first quantitative CAD code-generation benchmark (200 NL→CadQuery expert pairs) — and CADCodeVerify, a VLM self-Q&A 4-view-render refinement loop that gives GPT-4 a 7.30% PCD reduction and 5.5% compile-rate gain over prior single-image refinement.

## Storyline (5-piece)
- **Problem.** LLMs/VLMs generating CadQuery from natural language often misinterpret intent. Prior refinement is human-in-the-loop (Makatura/Nelson) or single-image-based (3D-Premise) — not scalable, often degrades compile rate. No quantitative CAD-code benchmark existed.
- **Contribution.** (1) CADPrompt: 200 hand-written 3D objects (selected from Wu 2021 modular CAD) each with NL prompt + expert CadQuery code, stratified by mesh / compile / geometric complexity. (2) CADCodeVerify: VLM auto-generates 2-5 yes/no validation questions from prompt → answers them with CoT looking at 4 renders (0/90/180/270°) → aggregates "No" answers into ameliorative feedback to refine code. (3) Demonstrates wins across GPT-4 / Gemini-1.5-Pro / CodeLlama.
- **Evidence (approach).** 3-step pipeline: generate → execute (compile-error repair, max N) → CADCodeVerify refine M times. ICP alignment + unit-cube normalization. Failed compile penalized PCD = √3, IoGT = 0.
- **Experiments.** GPT-4 few-shot: PCD 0.155 → **0.127** (-7.3%), IoGT 0.939 → 0.944, compile **96.0% → 96.5%**. 3D-Premise drops compile to 91.0%. Gemini few-shot: 3D-Premise drops compile 85% → 81.5%; CADCodeVerify holds 85%. CodeLlama with GPT-4 verifier: compile 67% → 73.5%. Hard subset: CADCodeVerify Refine-1 +9% compile vs 3D-Premise -20%. Ablation (100 subset): no Iref image → PCD 0.153 vs with → 0.126. HITL upper bound: PCD 0.137 → 0.120 (HITL only marginally better).
- **Analysis.** PCD/Hausdorff don't capture structural logic (e.g. small gap between table legs and top). Self-Q&A answer accuracy only 64-68% (verifier itself errs). Prompts contain absolute geometry ("about 2/3rd"), making scale invariance impossible.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | 3-step CADCodeVerify loop: generate → execute → self-Q&A refinement with 4 renders. | Pipeline overview. |
| 2 | 5 | figure | pipeline | GPT-4 qualitative example: target → initial code → CADCodeVerify-refined code with QA evidence. | Refinement effect on a real prompt. |
| 3 | 6 | table | data-stats | Table 1: CADPrompt 200-obj stats — Simple/Mod/Complex/V.Complex 17/39/87/57; mesh + line + token ranges. | Establishes benchmark scope. |
| 4 | 7 | table | headline-results | Table 2: median (IQR) PCD / IoGT / compile across GPT-4 / Gemini / CodeLlama with multiple feedback methods. | Establishes 7.3% PCD / 5.5% compile gain. |

CHECKED: figs/fig01_hero.png, figs/fig05_pipeline.png, figs/fig06_data-stats.png, figs/fig07_headline-results.png all exist.

## Takeaways for BenchCAD
- **Direct competitor**: ICLR'25 publishes 200-prompt CadQuery benchmark — must justify why we add a new one. Answers: (a) 200 → 20K verified (×100); (b) no family structure → 106-family registry; (c) IoGT = bbox overlap → rotation-invariant mesh IoU; (d) absolute prompts → scale-invariant prompts.
- **Borrow the stratification**: 3-axis difficulty (mesh complexity / compile complexity / geometric complexity) is a clean reporting template. We should mirror this for our easy/medium/hard.
- **Steal HITL upper-bound trick**: report PCD with human-in-the-loop refinement to bracket what an SOTA model could achieve. Great honest framing for our edit task.
- **CADCodeVerify is itself a baseline we can run** on our img2cq subset — it's just a refinement loop on top of any VLM, no training. Add this baseline.
- **PCD-doesn't-capture-logic** is their explicit limitation — direct support for our IoU + family-aware metric stack. Quote verbatim.

## One-line citation
`Alrashedy, Tambwekar, Zaidi, Langwasser, Xu, Gombolay (2025). Generating CAD Code with Vision-Language Models for 3D Designs. ICLR.`
