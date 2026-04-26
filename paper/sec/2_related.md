# §2 Related Work (draft v0)

> Target ≤ 1.0 page. 4 段。每段先一句话 cite + 定位,再一句话点弱点,最后一句话区分 BenchCAD。

---

## 2.1 Command-Sequence CAD Generation

The first wave of programmatic CAD generation operates on **command-sequence representations** of sketch-and-extrude operations. DeepCAD~\cite{Wu2021} introduces a 178K-model corpus of Onshape parts encoded as discrete operation tokens, and Text2CAD~\cite{Khan2024} extends DeepCAD with 660K natural-language annotations spanning four abstraction levels and trains a BERT-conditioned autoregressive transformer to emit those tokens. CAD-Coder~\cite{Guan2025} reformulates the same underlying data as **CadQuery** Python source and applies SFT + GRPO with a chain-of-thought prefix and Chamfer-distance reward, reaching mean CD 6.54$\times 10^{-3}$ on the Text2CAD test split.

## 2.2 The CadQuery-VLM Lineage

A parallel research program has driven the recent state-of-the-art in CadQuery code generation through three iterative releases by a single research lineage. **CAD-Recode**~\cite{Rukhovich2025} (ICCV'25) first established the CadQuery formulation for reverse engineering, fine-tuning a Qwen2-1.5B language model on a procedurally-generated corpus of 1M sketch-and-extrude scripts and reporting mean Chamfer distance 0.30 and IoU 92.0 on DeepCAD. **cadrille**~\cite{Kolodiazhnyi2026} (ICLR'26) extends this base by upgrading to Qwen2-VL-2B and unifying point-cloud, multi-view image, and text inputs in a single model, then introducing online reinforcement learning via Dr.CPPO with a piecewise IoU reward (R = 10 IoU on success, $-10$ on invalid output); the resulting cadrille-RL reaches DeepCAD image IoU 92.2 and Fusion360 image IoU 84.6 with invalidity rate at 0.0\%. **CADEvolve**~\cite{Elistratov2026} (Feb 2026) shares the same backbone and RL recipe but expands the training corpus from 46 hand-written CadQuery primitives to 2.7M scripts via a GPT-5-mini-driven evolutionary loop with four-stage validation, achieving DeepCAD image IoU 92.6 and Fusion360 image IoU 87.2. All three release model weights, training data, and inference scripts under permissive licences (Apache-2.0 for CAD-Recode and CADEvolve; CC-BY-NC-4.0 for cadrille); we evaluate the latest two on BenchCAD as transfer baselines (§\ref{sec:transfer}).

These works collectively demonstrate the viability of CadQuery as a generation target and establish $\sim$92\% IoU as the saturated ceiling on existing benchmarks. They share three structural limitations BenchCAD directly addresses. First, training data across the lineage is dominated by sketch + extrude operations — CAD-Recode's 1M procedural corpus exercises only sketch primitives plus Boolean union; CADEvolve's evolutionary expansion adds basic fillet, chamfer, and revolution but neither helical sweeps nor twist-extrusion (see Table~\ref{tab:op_coverage}). Second, evaluation uses unverified parsed code (DeepCAD test split) and lacks both family-level taxonomy and standard-table grounding, leaving the operation-richness gap and industrial-fidelity gap invisible to the reported metrics. Third, none **decouple sub-capabilities**: every prior benchmark scores a single end-to-end metric (CD, IoU, IR), so a model's score conflates visual perception, geometric abstraction, and code synthesis (§\ref{sec:capability}).

## 2.2 CAD Code-Generation Benchmarks

CADCodeVerify~\cite{Alrashedy2025} introduces \textbf{CADPrompt}, the first quantitative CAD code-generation benchmark — 200 natural-language prompts paired with expert CadQuery code, scored via point-cloud distance (PCD) and bounding-box IoU after ICP alignment. The same paper proposes a VLM self-questioning refinement loop, raising GPT-4 PCD by 7.3\% and compile rate by 5.5\%. Despite establishing a useful protocol, CADPrompt suffers from sample-size and design constraints: 200 examples is two orders of magnitude smaller than BenchCAD's verified split (20{,}143); samples are mesh-derived without family taxonomy or difficulty stratification; prompts contain absolute millimetre dimensions, leaking scale information that any size-aware model trivially exploits; and IoU is computed on axis-aligned bounding boxes, penalizing geometrically correct but axis-permuted solutions. Beyond CADPrompt, ad-hoc evaluations in CAD-Coder and CAD-Recode reuse the DeepCAD test split, which is unverified parsed code rather than execution-validated ground truth.

## 2.3 Vision-Language Spatial \& Code Benchmarks

Recent benchmark methodology in adjacent domains informs our design. MMSI-Bench~\cite{MMSIBench2026} evaluates 37 multimodal LLMs on 1{,}000 hand-curated multi-image spatial reasoning questions across an 11-task taxonomy, reporting a 67-point human-model gap and demonstrating that scaling model size yields negligible gains. AutoCodeBench~\cite{Chou2026} constructs a 3{,}920-problem multilingual code-generation benchmark via an automated LLM--sandbox pipeline (AutoCodeGen) and releases Lite/Complete subsets for differentiated evaluation regimes. Infinity-Chat~\cite{Hivemind2025} curates 26K real-world open-ended queries with 31K dense human annotations and reveals an "Artificial Hivemind" homogenization effect across 70+ models. We adopt three of their structural patterns: (i) explicit task taxonomy with per-task representatives (MMSI-Bench), (ii) Lite + Full split design for differentiated evaluation cost (AutoCodeBench), and (iii) named, quantitative finding as the paper's punch line (all three).

## 2.4 Position of BenchCAD

BenchCAD occupies a vacant intersection: a CAD code-generation benchmark that is simultaneously (i) **execution-verified at scale** (20{,}143 parts at IoU $\geq 0.99$), (ii) **standard-anchored** (55\% of families bound to ISO/DIN/EN/ASME/IEC specification tables — see Table~\ref{tab:standards}), (iii) **operation-rich** (45+ CadQuery operations, vs.~2--5 in prior corpora), and (iv) **capability-decomposed** (5 tasks isolating visual reconstruction, parametric abstraction, and code synthesis along the image$\to$code causal chain — see Table~\ref{tab:capability}). To our knowledge, BenchCAD is the first CAD code-generation benchmark to expose a capability-diagnostic protocol; this is a design contribution independent of the dataset itself, and orthogonal to the model-side training innovations of CAD-Coder and CAD-Recode.

---

## TODO
- bibkeys 占位 (Wu2021, Khan2024, Guan2025, Rukhovich2025, Alrashedy2025, MMSIBench2026, Chou2026, Hivemind2025) — main.bib 待补
- 是否单列一段 "GenCAD / Onshape ecosystem"?currently 隐于 §2.1
- 是否提 Query2CAD / CAD-Assistant / CAD-MLLM / CADmium / OBJ2CAD?目前为节省篇幅没提,可在 supplementary 加一段
- §2.3 是否单挂一段 "human-curated benchmarks"?可以,但目前 stretched 到 §2.3 + §2.4 末尾足够
