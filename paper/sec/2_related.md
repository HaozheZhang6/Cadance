# §2 Related Work (draft v0)

> Target ≤ 1.0 page. 4 段。每段先一句话 cite + 定位,再一句话点弱点,最后一句话区分 BenchCAD。

---

## 2.1 CAD Code Generation

The first wave of programmatic CAD generation operates on **command-sequence representations** of sketch-and-extrude operations. DeepCAD~\cite{Wu2021} introduces a 178K-model corpus of Onshape parts encoded as discrete operation tokens, and Text2CAD~\cite{Khan2024} extends DeepCAD with 660K natural-language annotations spanning four abstraction levels and trains a BERT-conditioned autoregressive transformer to emit those tokens. CAD-Coder~\cite{Guan2025} reformulates the same underlying data as **CadQuery** Python source and applies SFT + GRPO with a chain-of-thought prefix and Chamfer-distance reward, reaching mean CD 6.54$\times 10^{-3}$ on the Text2CAD test split. CAD-Recode~\cite{Rukhovich2025} extends the CadQuery formulation to point-cloud reverse engineering, producing a 1M procedural training corpus and a 10$\times$ improvement in mean Chamfer distance over CAD-SIGNet on DeepCAD/Fusion360/CC3D.

These works demonstrate the viability of CadQuery as a generation target, but share three structural limitations BenchCAD directly addresses. First, all four are restricted to **sketch + extrude operations** (CAD-Recode adds Boolean union; none cover revolve, sweep, loft, twist-extrude, helical sweep, or shell — see Table~\ref{tab:op_coverage}). Second, training data is parsed from a single corpus (DeepCAD/Onshape) or LLM-synthesized from it, inheriting the same primitive bias and lacking explicit family-level structure or standard-table grounding. Third, none **decouple sub-capabilities**: every benchmark scores a single end-to-end metric (CD, IoU, IR), so a model's score conflates visual perception, geometric abstraction, and code synthesis (§\ref{sec:capability}).

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
