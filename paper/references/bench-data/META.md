# BenchCAD Reference Survey — Cross-Paper Synthesis

Read date: 2026-04-27 · 60 papers across 7 categories · Track: NeurIPS 2026 D&B

Coverage: A-CAD ([cad_coder][cad_recode][cadcodeverify][cadevolve][cadrille][cadtalk][text2cad][text2cadquery][blenderllm_cadbench][query2cad][histcad][mv2cyl]) · B-3D ([cap3d][objaverse_xl]) · C-code-gen ([autocodebench][bigcodebench][codemmlu][codesense][convcodeworld][livecodebench][repobench][scicode][spider2][swebench_pro]) · D-VLM ([blink][charxiv][gmai_mmbench][ii_bench][infinity_chat][mathvista][math_v][mega_bench][mllm_compbench][mm_niah][mmiu][mmmu_pro][olympiadbench][sportr][sportu][visual_cot][vstar]) · E-spatial ([ego3d_bench][gsr_bench][mindjourney][mmsi_bench][msqa_msr3d][spatialeval][spatialqa][spatialrgpt]) · F-D&B-template ([agentbench][agentboard][bbeh][care_pd][gaia][gpqa][mmlu_pro][rigorous_agent_bench][webarena_verified]) · G-math ([hardmath][usamo_proof]).

---

## 1. Pattern Catalog (figure-level)

### 1.1 Hero panel (page 1 teaser)
- **Function:** 30-second pitch — sells the entire paper before §1.
- **Strong examples:** [infinity_chat] PCA "time is a river" cluster (Best Paper move), [text2cad] 4-level NL→CAD progression, [mmsi_bench] 4-panel composite (examples + error pie + bar w/ human line), [mathvista] radar+grouped-bars combo.
- **Variants:** iconic single image ([infinity_chat]), 4-panel grid ([mmsi_bench][gaia]), annotated worked example ([scicode][bigcodebench][gpqa]), pipeline-as-hero ([cadcodeverify][query2cad]), three-claim-stack ([mmlu_pro] difficulty + robustness + CoT-unlock in one).
- **What works:** ONE memorable visual whose meaning is obvious in 5 seconds. [infinity_chat]'s PCA is the gold standard — single phenomenon, single image, instantly quotable. Multi-panel composites work only when each panel sells a distinct claim ([mmsi_bench], [mmlu_pro]).
- **What fails:** [agentboard] tries to cram task-suite + analytical-panel + curves into Fig 1; ends up illegible. [vstar] hero-as-pipeline competes with §3 figure.

### 1.2 Gap-vs-prior table
- **Function:** Kill all related-work in one table. Rows = competing benches, cols = orthogonal axes (size, modalities, splits, granularity, license). ✓/✗ checkmarks.
- **Strong examples:** [gmai_mmbench] vs Medical-Diff-VQA / PathVQA / MMMU H&M, [mmiu] vs Video-MME / MIRB / MUIRBENCH / MileBench, [olympiadbench] vs SciBench / MMMU / MathVista / AGIEval, [blink] vs MMMU / MathVista / SEED, [histcad] vs DeepCAD / Text2CAD on 5 features.
- **What works:** 4–7 axes, every axis is something prior work *lacks*. The author's bench is always the only row with all ✓.
- **What fails:** [cad_recode] doesn't include one — leaves position-vs-prior fuzzy. Reviewers hate this.

### 1.3 Taxonomy / skill-tree diagram
- **Function:** Memorable structure imposed *before* numbers; reviewers cite the tree.
- **Strong examples:** [agentbench] Code/Game/Web 3-grouping, [infinity_chat] 6×17 open-ended tax-tree, [mmsi_bench] 3×3 element-dimension grid, [gmai_mmbench] queryable lexical tree (modality × task × department × granularity), [mega_bench] hierarchical tree (application × skill × input × output), [mmiu] radial taxonomy ring (7 relationship types).
- **What works:** ≤3 buckets ([agentbench]) OR a deep tree exposed as queryable filter ([gmai_mmbench]). Middle ground (52 tasks in [mmiu]) drew reviewer pushback for redundancy.

### 1.4 Construction pipeline diagram
- **Function:** Methodology cookbook — readers will copy this. Single-figure proof of effort.
- **Strong examples:** [autocodebench] 4-stage reverse pipeline (Solution → test → problem → filter), [mmlu_pro] 4-stage funnel (filter → integrate → augment → review), [bigcodebench] 3-stage human-LLM, [gpqa] writer→2-expert→3-non-expert annotation, [cap3d] BLIP2 → CLIP-filter → GPT-4 fuse, [webarena_verified] old-vs-new evaluator schematic, [cadrille] 3-stage pretrain→SFT→RL.
- **What works:** explicit stage boundaries with tool/model labels per stage; arrows show data flow. [mmlu_pro]'s funnel is the cleanest — reader can re-implement from the figure.

### 1.5 Headline radar / bar / heatmap
- **Function:** "ranking on a single image."
- **Strong examples:** [agentbench] per-env relative-to-best radar, [agentboard] 6-skill sub-skill radar, [codemmlu] per-task radar across frontier models, [livecodebench] 4-scenario radial chart, [mega_bench] per-axis radar of 5 flagship models, [mathvista] per-skill radar, [mmiu] heatmap (model-cluster × task-cluster), [mm_niah] context-length × depth heatmap.
- **What works:** radar for ≤8 axes; heatmap for 2-D continuous spaces; bar for direct ranking. Always pair with a human-line so the gap is visible.

### 1.6 Failure case grid
- **Function:** Concrete error inventory; converts qualitative observation into citable structure.
- **Strong examples:** [mathvista] error breakdown (vision/reasoning/calc/knowledge), [mmlu_pro] 39%-reasoning/35%-knowledge/12%-compute pie, [usamo_proof] stacked bar of first-failure categories, [mmsi_bench] 4 named error modes (grounding/overlap-matching/situation-transformation/spatial-logic), [sportr] error pie (Visual Perception > Hallucination > Reasoning), [cad_coder] qualitative target vs Text2CAD vs zero-shot vs CAD-Coder, [swebench_pro] trajectory-level failure clustering (wrong-fix/wrong-file/incomplete).
- **What works:** named categories with explicit percentage mass; one paragraph of analysis per category, not an essay. Provides the actionable hook for follow-up papers.

### 1.7 Scaling curve / ablation
- **Function:** Demonstrate non-saturation, justify dataset size, prove component value.
- **Strong examples:** [objaverse_xl] PSNR vs #pretrain assets 1k→10M (monotone, no plateau), [text2cadquery] EM vs LM size 124M→7B, [cad_coder] 8K-curated vs 70K-medium quality-over-quantity, [mmsi_bench] InternVL3 78B vs 1B = +1.5% scaling cliff, [autocodebench] DeepSeek-V3 multi-turn refinement +11.6 pts.
- **What works:** clean log-x axis, monotone-or-flat curve, ≥4 points so trend is obvious. Pair with "scaling cliff" or "no saturation" punchline.

### 1.8 Human-vs-model gap
- **Function:** The headline. Single number or bar pair that anchors the contribution.
- **Strong examples:** [gaia] humans 92% vs GPT-4 15%, [blink] humans 95.7 vs GPT-4V 51.3, [mmsi_bench] humans 97.2 vs GPT-5 41.9, [gpqa] experts 65/74% vs Google-armed non-experts 34%, [math_v] humans 68.8 vs GPT-4o 30.4 (38-pt gap), [ii_bench] humans 90 vs GPT-4o 74.8, [olympiadbench] best LLM 17.23%, [usamo_proof] best <30%.
- **What works:** the gap *is* the contribution. State it in the abstract, repeat it on page 1, return to it in the conclusion. Smaller gaps (<10 pts) are not worth the same emphasis.

### 1.9 Correlation scatter (proxy validation)
- **Function:** Justify a cheap proxy by showing it tracks the expensive one.
- **Strong examples:** [convcodeworld] ConvCodeBench static replay vs live env (Spearman ~0.95), [bigcodebench] Pass@1 calibration between Complete/Instruct (0.982), [charxiv] descriptive vs reasoning per-model scatter, [codemmlu] CodeMMLU vs HumanEval per model + CoT effect.
- **What works:** strong correlation justifies the proxy; weak correlation reveals a *new* axis to measure (descriptive ≠ reasoning).

### 1.10 Per-difficulty / per-skill breakdown table
- **Function:** Defeat aggregate-collapse. Replace one number with a grid that exposes blind spots.
- **Strong examples:** [text2cad] L0–L3 prompt levels, [sportu] easy/medium/hard columns with hard-column collapse, [scicode] main vs subproblem (7.7% vs 28.5%), [bbeh] harmonic mean across 23 tasks (penalises lopsided strengths), [hardmath] per-problem-type accuracy (ODEs hardest), [livecodebench] per-month time-window Pass@1.
- **What works:** rows = models, cols = difficulty/skill, bold per-column-best (not per-row-best), include human bottom row.

### 1.11 Modality / input-format ablation
- **Function:** Show what the model actually uses. Same-question across input formats exposes shortcut behaviour.
- **Strong examples:** [spatialeval] TQA / VQA / VTQA triple (text / image / both), [mmmu_pro] standard vs vision-only-screenshot, [convcodeworld] 3×3 feedback grid (compile × execution × verbal), [mllm_compbench] per-image describe → compare 2-stage ablation, [mm_niah] image-needle vs text-needle.
- **What works:** make the *same* item answerable both ways; report the cross-modality delta as a finding ("VLM-vs-LLM-backbone gap is negative on image-only" — [spatialeval]).

### 1.12 Gallery / qualitative side-by-side
- **Function:** Visual proof that the bench is what it claims to be; supplements the quantitative table.
- **Strong examples:** [cadevolve] op-coverage gallery (extrude/revolve/loft/sweep/shell/fillet/chamfer/booleans/patterns), [text2cad] L0–L3 reconstructions vs DeepCAD, [cap3d] caption-3D pair gallery, [blenderllm_cadbench] chair/burger/lamp 6-model comparison, [objaverse_xl] dense scene of objects across categories.
- **What works:** ≥6 examples with clear category labels; bold the failures in red. CAD-coverage galleries are particularly persuasive against the sketch-extrude monoculture critique.

---

## 2. Storyline Patterns (paper-level)

### 2.1 Hook templates (4 types observed)
1. **Visual-iconic hero** ([infinity_chat], [mmsi_bench], [text2cad]) — let the cover image carry the pitch.
2. **Gap-table-on-page-2** ([autocodebench], [gmai_mmbench], [mmiu]) — kill prior work first, then build.
3. **Failure-of-SOTA hook** ([blink] "MLLMs can see but not perceive"; [gaia] "humans 92% / GPT-4 15%"; [olympiadbench] "GPT-4V 17.23%"; [usamo_proof] "best LLM <30%").
4. **Saturation-replacement hook** ([mmlu_pro] "MMLU saturated"; [bbeh] "BBH >90%"; [livecodebench] "HumanEval saturated + contaminated"; [mmmu_pro] "MMMU 69.1% suggests near-human"; [swebench_pro] "SWE-Bench-Verified saturating"; [spider2] "Spider 1.0 91.2% vs ours 21.3%").

### 2.2 Contribution structures (typical D&B 3-piece)
- **Real/curated data + explicit taxonomy + high-quality GT** is the modal pattern across [gpqa][gmai_mmbench][infinity_chat][mmsi_bench][olympiadbench].
- **Surface variants:**
  - dataset-only ([objaverse_xl][cap3d][text2cad]).
  - data + model + leaderboard ([cadrille][cadevolve][text2cadquery][blenderllm_cadbench]).
  - data + toolkit + analytical UI ([agentboard][webarena_verified]).
  - data + audit-of-prior-bench ([webarena_verified][rigorous_agent_bench][mmlu_pro]).
- **3-piece contributions** consistently sell better than 1-piece — even pure-bench papers add a baseline method ([cadcodeverify], [vstar], [spatialqa]).

### 2.3 Section-level moves
- **Intro** = problem (3 specific gaps) → contribution (numbered list) → headline gap number. [gaia][bbeh][mmlu_pro] do this in <2 pages.
- **Method** = pipeline diagram first, prose second. [autocodebench][mmlu_pro][cap3d] all let the figure carry §3.
- **Eval** = leaderboard + per-slice + headline plot. ≥30 models is the 2025-26 bar ([spatialqa] ran 41, [mmsi_bench] 37, [bigcodebench] 60). Anything <15 reads as small.
- **Analysis** = numbered "N findings" or named error modes ([gmai_mmbench] 5 insufficiencies, [mmsi_bench] 4 error modes, [spatialeval] 4 findings, [agentbench] 2 levers).
- **Limitations** = short, cite specific reviewer-anticipated objections. [sportr][sportu] embed limitations at subsection ends rather than a separate section — Hanjie-Chen-lab style.

---

## 3. Critical Review

What 60 papers consistently DO that hurts D&B quality.

### 3.1 Tiny "real-world" eval sets passed off as benchmarks
- [blenderllm_cadbench] CADBench is **200 forum-scraped** items — too small to be statistically stable. Reviewer-magnet for rejection.
- [cadcodeverify] CADPrompt is **200 hand-written** — directly competes with our space, but variance dominates the metric.
- [query2cad] custom eval is <100 prompts.
- [vstar] V*Bench is 191 items; authors themselves note reviewer pushback.
- [usamo_proof] 6 problems × 11 models — fine for a workshop but not a top-venue D&B.
- **BenchCAD lesson:** 1.4k curated subset is the *minimum* defensible scale; full 17.8k is the right primary set.

### 3.2 Annotation thinness
- Most VLM benches have 1 anno/item. [infinity_chat]'s **25 annotators per item** is the quality high-water mark and won Best Paper at NeurIPS D&B 2025 partly for it.
- [gpqa] uses 2 expert + 3 non-expert validators per item.
- [mmsi_bench] uses 3-reviewer audit.
- [mmlu_pro] uses 2-phase expert review (correctness + LM-flagged false-negative).
- **Pattern:** if you cannot do 25-anno, document multi-stage review explicitly. Reviewers count.

### 3.3 Headline-result inflation (cherry-picked top-1 model)
- Many CAD papers ([cad_coder][cad_recode][text2cad]) frame headlines around their own trained model rather than the bench-vs-models gap. Reviewers see this as method-paper-in-D&B-clothing.
- [text2cad] reports F1 + CD on a *single trained baseline* (DeepCAD reformulated) — looks impressive but doesn't validate the bench's discriminability.
- **Fix:** report the *spread* between top frontier models ([mmlu_pro]'s "1%→9% discriminability" framing).

### 3.4 Eval cost not transparent
- Most papers fail to publish $/run for full eval. [convcodeworld] is the rare exception — 1.5% of human cost stated, ConvCodeBench static-replay quantified.
- [webarena_verified] publishes 17%-cost Hard subset that preserves rank fidelity.
- **Pattern:** without cost transparency, reviewers assume eval is expensive and adoption suffers.

### 3.5 Closed eval / leaderboard gameability
- [gaia] holds out 300/466 with private GT — gold standard for contamination defense.
- [mathvista] testmini public + test-5.1k held-out.
- [swebench_pro] three-tier (public / held-out / commercial-API-only).
- **Counter-examples** (no held-out):  [text2cad][text2cadquery][cad_recode][cadrille][cadevolve] all fully public eval. Vulnerable to RL-on-test contamination.

### 3.6 Coverage claims that don't hold up
- [text2cad] claims "first text→parametric CAD" but inherits DeepCAD's rect/cyl bias — rectangles and cylinders dominate; arc/loft/revolve are sparse.
- [cad_recode] explicitly limits to sketch+extrude — but framing implies full CAD coverage.
- [cadrille] "multimodal" but SFT data backbone is sketch+extrude-only via CAD-Recode + DeepCAD — RL can't add ops the SFT model never saw.
- **Pattern:** "multimodal" / "multi-task" / "comprehensive" claims need a coverage *table*, not just a sentence.

### 3.7 Missing license / ethics
- [objaverse_xl] is the gold standard — explicit NSFW/face/photogrammetry-hole CLIP filters, license-clean subsets reported separately.
- [care_pd] models the IRB framing.
- [text2cad][text2cadquery] inherit DeepCAD's mixed-license substrate without clear filtering. Fusion360 Gallery has its own CC-BY constraints.
- **BenchCAD risk:** Fusion360 derivatives need explicit license card — open question 5.

### 3.8 LLM-as-judge calibration silently broken
- [usamo_proof] explicitly shows LLM judges (o4-mini, o3-mini, Claude-3.7) **inflate proof scores by up to 20×** with OpenAI bias.
- [infinity_chat] shows LM-judges agree confidently exactly where humans diverge.
- [query2cad] BLIP2-VQA grader has documented false-negative rate.
- **Pattern:** if you use an LM judge, you must publish a calibration scatter vs human; otherwise reviewers will reject. BenchCAD's deterministic IoU/exec-pass metric is a reviewer-pleaser here.

### 3.9 Single-aggregate-number reporting
- [mathvista] explicitly warns against collapsing to ALL%. Yet many papers ([objaverse_xl] zero-shot OOD; [cap3d] win-rate) lead with one bar.
- [mmiu] / [mega_bench] / [agentbench] all publish per-axis radars but the abstract still anchors on one number.
- **Fix:** report aggregate **AND** per-skill in the abstract; lead with both ("X overall, but Y on hard column").

### 3.10 N=200 forum scrape antipattern
- [blenderllm_cadbench] 200 forum-sourced CADBench items.
- [cadcodeverify] 200 hand-written CADPrompt items.
- [query2cad] <100 hand-curated.
- All three are below the 1k threshold reviewers now expect.

### 3.11 Construction effort not quantified
- [mmsi_bench] explicitly reports "6 researchers × 300+ hours" inspecting 120K candidates → 1K final. Effort-as-credibility.
- [mmlu_pro] Table 1 reports per-source issue counts (350 incorrect, 1953 false-negatives, 862 bad-format).
- **BenchCAD opportunity:** quantify family-curation effort + pre-flight build-test passes per family.

### 3.12 Eval doesn't actually require the claimed modality
- [mmmu_pro] showed MMMU has many items text-only-LLMs solve at chance — i.e. "multimodal" was a marketing claim. They filtered down 10,500 → 5,919 image-dependent → 1,730 truly visual.
- [ego3d_bench] explicitly filters single-view-answerable items.
- [text2cad]'s prompts often spell out exact dimensions, making the "image" optional — image-conditioning is theatrical.
- **Pattern:** every multimodal bench should run a same-question text-only LLM ablation; items the LLM solves at >chance are *not* probing the visual axis. BenchCAD must do this.

### 3.13 No statistical significance / CIs
- [webarena_verified] is the rare bench shipping macro-average + 95% bootstrap CIs and Cohen's κ=0.83 for annotator agreement.
- [usamo_proof] uses paired permutation tests for rank confidence.
- Most other papers report point estimates only. Reviewers in 2025–26 increasingly demand CIs.

### 3.14 "Held-out" claimed but trivially recoverable
- [livecodebench] post-cutoff date strategy works because LeetCode is fresh. Procedural CAD has no analogous "cutoff" — version-stamping seeds is the closest analog (Decision 10).
- [text2cadquery] inherits Text2CAD's full split as fully public — straightforward to RL-on-test.

---

## 4. Distilled BenchCAD Style

| # | Decision | Adopt-from | Deviate-from | Rationale |
|---|---|---|---|---|
| 1 | **Hero figure: 4-panel composite — family-tree (106 → 6 buckets) + worked easy/hard pair + scaling-cliff curve + human-line bar.** | [mmsi_bench] 4-panel, [mmlu_pro] 3-claim composite, [text2cad] L0–L3 progression | [infinity_chat] single iconic image (we lack one phenomenon) | We have multiple sub-claims (op coverage, IoU verification, human gap); 4-panel composite carries them; single image would undersell. |
| 2 | **Lead the abstract with TWO sticky numbers, not one.** "Frontier LLMs reach X% IoU≥0.99 vs CAD-engineer Y%; on the hard families they collapse to Z%." | [gaia] 92/15, [blink] 95.7/51.3, [bbeh] 9.8/44.8 | [autocodebench] single 52.4 number, [olympiadbench] single 17.23 | Two numbers (overall + hard-column) defeat aggregate-collapse and replicate [mmlu_pro]'s 1%→9% discriminability claim. |
| 3 | **Family registry exposed as queryable lexical tree (106 → 6 macro-buckets).** | [gmai_mmbench] queryable lexical tree, [agentbench] Code/Game/Web 3-grouping, [infinity_chat] 6×17 | [mmiu] 52-task cardinality (drew pushback) | 106 is too many for hero figure; 6 macros for narrative + full tree as appendix filter mirrors [gmai_mmbench]'s "but how does it do on flanges only?" reviewer-hook. |
| 4 | **Five-task contribution structure: img2cq + json2cq + edit + qa + repair, sharing the same 17.8k parts pool.** | [livecodebench] 4-scenario shared pool, [agentbench] 8-env shared protocol, [spider2] full+Lite+Snow tiered split | [bigcodebench]'s 1140 single-task, [autocodebench]'s single Pass@1 | Shared pool is the [livecodebench] move that converts a "yet another bench" into a "holistic capability suite." |
| 5 | **Dual eval: BenchCAD-Mini (1.4k curated) for fast iteration + BenchCAD-Full (17.8k) for leaderboard, with rank-preservation proof.** | [autocodebench] Lite+Complete, [bbeh] BBEH-Mini 460 ex, [webarena_verified] Hard 137-task, [mathvista] testmini-1k | [text2cad] no Mini split, [cad_recode] no fast-iter set | Lite/Mini is now the 2024–26 norm; reviewers complain about cost without one. Rank-preservation correlation scatter borrowed from [webarena_verified]. |
| 6 | **Difficulty stratification: easy / medium / hard with per-column reporting AND a "hard-column collapse" punchline.** | [text2cad] L0–L3, [sportu] easy/medium/hard, [bbeh] BBEH harmonic-mean penalising lopsided | [autocodebench] N-pass-sample-based (we can do this too as supplement) | Maps to our family.sample_params(diff, rng). Per-column reporting + bold the hard-column gap is sticky. |
| 7 | **Headline metric: rotation-invariant mesh IoU≥0.99 pass-rate AS PRIMARY, with chamfer-distance + exec-pass + topology-match as secondary.** | [gaia] single deterministic check, [cad_recode] Mean/Median CD + IoU + IR triplet | [cad_coder] CD-only, [cadcodeverify] PCD/IoGT (their own limit-section) | Geometric IoU is reviewer-defensible (not LM-judge); IoU≥τ pass-rate aligns with [autocodebench] Pass@1 framing. |
| 8 | **No LLM-as-judge for primary scoring.** Reserve LM-judge for an *optional* "design-intent" qualitative subset with human calibration scatter. | [usamo_proof] LM-judge inflation finding, [infinity_chat] LM-judge calibration breaks where humans diverge | [text2cad] GPT-4V 2-alternative eval, [cap3d] CLIP-filter-as-scorer | Deterministic geometry is our killer feature; using LM-judge would surrender it. |
| 9 | **30+ model evaluation lineup: Claude-3.7/4, GPT-4o/5, DeepSeek-V3/R1, Gemini-2.5, Qwen2.5-Coder family (0.5/1.5/7/32B), Llama-3.1-70B, plus CAD-specialists (CAD-Recode, cadrille, Text2CAD, CAD-Coder).** | [cad_coder] zero-shot LLM lineup, [bigcodebench] 60 LLMs, [spatialqa] 41 VLMs, [mmsi_bench] 37 MLLMs | [cad_recode] just 4 baselines (insufficient by 2026 standards) | 30 is the 2025–26 floor for D&B. Sweeping a Qwen2.5-Coder size family enables a [mmsi_bench]-style scaling-cliff finding. |
| 10 | **Hold-out 10% private split + canary string in every prompt; ship 90% public.** | [gpqa] canary + private DIAMOND, [gaia] 166 dev / 300 hidden, [swebench_pro] held-out + commercial tier, [mathvista] testmini public + test-5.1k hidden | [text2cad][cad_recode] no private split | Standard 2025–26 contamination defense. We lose nothing; gain credibility. |
| 11 | **Pre-flight rule (already enforced in CLAUDE.md) becomes a §3 figure: build-test → geometry-validity → single-solid → vis-text-agreement.** | [cadevolve] 4-stage validation, [mmlu_pro] 4-stage construction funnel, [gpqa] writer→validator pipeline | [text2cad] no validation funnel diagram (just text) | Visualizes the engineering investment that produced 106 working families. Cheap wins. |
| 12 | **"BenchCAD-Verified" rigor framing: audit Text2CAD/CAD-Recode/CADPrompt for issues, publish issue table with counts, position our methodology as the cleanup.** | [webarena_verified] issue taxonomy table (κ=0.83), [rigorous_agent_bench] ABC checklist, [mmlu_pro] Table 1 issue counts | [text2cadquery] doesn't audit predecessors | "Verified" is a recognized 2025–26 genre. Audit gives us a defensible related-work table that politely demolishes prior CAD benches. |
| 13 | **Error taxonomy with explicit percentages: wrong-primitive / wrong-topology / wrong-dimension / wrong-constraint / wrong-axis.** | [mmlu_pro] 39%-reasoning/35%-knowledge/12%-compute, [mmsi_bench] 4 named error modes, [sportr] error pie | [cad_coder] qualitative case-study only | Replaces "limitations" essay with citable category mass. Every follow-up paper now has an attack vector. |
| 14 | **Construction-pipeline §3 figure: registry → builder.build_from_program → IoU verifier → 4-view render → 5-task SFT/eval pairs.** | [autocodebench] 4-stage pipeline, [bigcodebench] 3-stage human-LLM, [cap3d] BLIP2→CLIP→GPT-4 chain | [cadrille] pipeline buried in text | Methodology cookbook. Reviewers will copy this. |
| 15 | **Triple-modality eval (image-only / json-only / both) with redundant-info ablation.** | [spatialeval] TQA/VQA/VTQA framing, [mmmu_pro] vision-only screenshot setting, [convcodeworld] 3×3 feedback grid | [text2cad] text-only, [cad_recode] point-cloud-only | The cleanest way to expose whether vision contributes. Critical for reviewers who suspect VLMs ignore the image. |
| 16 | **Scaling-cliff figure: Qwen2.5-Coder 0.5/1.5/7/32B on x-axis, IoU pass-rate on y-axis.** | [text2cadquery] 124M→7B clean curve, [objaverse_xl] 1k→10M no-saturation, [mmsi_bench] 78B vs 1B = +1.5% cliff | [cad_recode][cadrille] no scaling sweep | One-figure-headline. If scaling fails to lift parametric accuracy, that's our [mmsi_bench]-grade punchline. |
| 17 | **Human topline: 3 CAD-engineer-hour budget on a 200-prompt subset → headline number.** | [gaia] 92% humans on 466 items, [gpqa] 65/74% experts vs 34% non-experts (37min web-allowed), [mmsi_bench] 97.2% humans, [charxiv] human 80.5 / GPT-4o 47.1 | [text2cad] no human number | Anchors the human-vs-model gap that drives the abstract. Open question 4 covers the cost. |
| 18 | **Limitations embedded at subsection ends, not a separate §.** | [sportr][sportu] Hanjie-Chen-lab style | [text2cad] / [cad_coder] separate limitations | Keeps focus on contribution; pre-empts reviewer objections without flagging them as red flags. |
| 19 | **Shipped artifacts: HuggingFace dataset (already done: cad_iso_106 + cad_simple_ops_100k) + Synth Monitor UI + 5-task evaluation harness + leaderboard URL.** | [agentboard] analytical web panel, [autocodebench] open sandbox + Lite/Complete, [webarena_verified] JSON schema + comparators | [cad_recode] training-corpus-only release | Long-tail-citation move. Synth Monitor is already built; framing it as a first-class deliverable is free credibility. |
| 20 | **Position vs HistCAD as orthogonal: their value = constraint representation, our value = code-gen evaluation harness + op-diversity coverage.** | [cad_recode] vs CAD-SIGNet positioning | [text2cadquery] doesn't differentiate sharply enough | [histcad] is our closest contemporary peer; we must differentiate explicitly. |

---

## 5. Open Questions

- Leaderboard? — gh-pages live or one-shot table?
- LM-judge for design-intent subset — include or skip v1?
- Fusion360 license card — derivative-OK clause sufficient or need Autodesk sign-off?
- Human topline cost — 3 engineers × 200 prompts × estimated 8 min/prompt ≈ 80 hours; budget?
- Hard-column threshold — define "hard" by family.difficulty='hard' OR by N-pass-sampling on a frontier model (cf. [autocodebench])?
- Hold-out split mechanic — version-stamp procedural seeds OR maintain private GT via online judge?
- Repair task — include? Currently 4 tasks (img2cq/json2cq/edit/qa); [livecodebench]-style repair adds completeness but cost.
- Contamination check — re-evaluate prior CAD benches' eval items against our families to estimate overlap (cf. [verify_180k_no_overlap.py] already exists).
- Canary string format — embed in CadQuery comment OR in JSON metadata field?
- Mini subset selection — stratified by family OR by model-discrimination (Lite-style high-discrimination items per [autocodebench])?
- "Verified" framing — tie to a named methodology contribution (e.g. "BenchCAD Hygiene Checklist") OR keep implicit?
- Multi-view convention — 4-view (current: front/right/top/iso) OR 8-view (6-ortho + 2-iso, cf. [cadevolve])?
- Sub-skill axes for radar — what 5–7 axes? Sketch / extrude / fillet-chamfer / boolean / pattern / loft-sweep / dimension is one candidate.
- Open-source model RL training — provide an SFT split (cf. [sportr]) or stay eval-only?
