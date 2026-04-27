# BenchCAD — Draft Intro v3 (NeurIPS 2026 E&D Track, Hanjie-voice pass)

> v3 changes vs v2 (style now mimics Hanjie Chen's SportR/SPORTU intros):
> - 5 → **3 contribution bullets** (her standard threefold)
> - 第 2 段加 **pyramid metaphor**(perception / parametric abstraction / code synthesis)
> - 第 1 段结尾收紧到 **1 个具体小例子** (M8 flange + bore ratio off)
> - 段首全部 thesis statements;长句 + 破折号插语;"we" 主导
> - 数字密集化(20,143 / 106 / 55% / 45+ / 30+ / 162K / 433 / 5)
> - 排比"While X..., Conversely Y..., Furthermore Z..." 列 prior gap (her signature)
> - 主 finding 提前到 intro 末段(她"X remain modest, suggesting Y is far from solved" 句式收尾)
> - Vision Bottleneck 命名保留(BenchCAD 独家 sticky term),但用 metaphor framing 包装
> - v2 backup at `draft_intro_v2.md.bak`

> Working title (pick one):
> 1. **BenchCAD: An Execution-Verified, Capability-Decomposed Benchmark for Programmatic CAD**
> 2. **BenchCAD: Diagnosing Vision, Parametric, and Code-Synthesis Capabilities of LMs on Manufacturing-Grade CAD**
> 3. **BenchCAD: A Standard-Anchored Parametric CAD Benchmark for Vision-Language Models**

---

## 1. Introduction

Programmatic computer-aided design — writing parametric scripts in CadQuery, OpenSCAD, or Fusion's Python API that compile to manufacturable solid geometry — has become the natural interface between large language models and the physical-design pipeline. A vision-language model (VLM) that reads an engineering sketch, emits executable CAD code, answers dimensional queries about that code, and revises its own output to natural-language instructions would compress weeks of mechanical drafting into seconds, and several recent works have begun to deliver pieces of this promise [Khan et al., 2024; Guan et al., 2025; Rukhovich et al., 2025; Alrashedy et al., 2025]. Yet a careful reader of these benchmarks notices an awkward pattern: the models that score highest on Chamfer distance often produce parts that *look* correct in renders but fail every parametric query against the ground truth. Asked to reconstruct a flanged bushing from four canonical views, a state-of-the-art reasoning model emits a CadQuery script whose flange diameter, bore ratio, and chamfer placement are all wrong by 5--20\% — and yet the rendered solid is visually convincing enough to pass a single end-to-end metric. **The geometry passes the eye; it fails the calliper.**

This pattern is invisible to existing CAD code-generation benchmarks because they collapse three distinct capabilities into a single score. We argue that the image-to-code pipeline is best understood as a three-rung *parametric pyramid* — at the base, **visual perception and 3D reconstruction**, where the model integrates four orthographic views into a coherent volumetric understanding; in the middle, **geometric-to-parametric abstraction**, where it identifies the parametric structure underlying that volume (which dimensions are bores, which are wall thicknesses, which are ratios fixed by industrial standards); and at the top, **parametric-to-code synthesis**, where it translates the parametric description into syntactically valid, executable CadQuery code. A single Chamfer-distance score collapses all three; it tells us a model failed but not *which rung gave way*. Prior CAD code-generation benchmarks reside near the base of this pyramid — Text2CAD [Khan et al., 2024] supplies natural-language conditioning for sketch+extrude command sequences over DeepCAD; CAD-Coder [Guan et al., 2025] applies SFT and GRPO with a Chamfer reward to produce CadQuery code from text; CAD-Recode [Rukhovich et al., 2025] reverse-engineers point clouds into CadQuery via a 1M-sample procedural training corpus — but none of them probe the middle rung directly, and none isolate the rungs from one another.

Three structural limitations compound this measurement gap. **While** every existing CAD code-generation corpus is dominated by sketch-and-extrude operations — DeepCAD, Text2CAD, CAD-Coder, and CAD-Recode collectively cover only two distinct CadQuery primitives and offer no revolution, lofting, sweeping, twist-extrusion, helical sketches, or shells, the operations that distinguish a real industrial part from a stack of boxes — real engineering practice routinely composes 20+ such operations within a single component. **Conversely,** the benchmark with the broadest manual coverage, CADPrompt [Alrashedy et al., 2025], contains only 200 expert-authored examples without family taxonomy, difficulty stratification, or scale-invariant prompts; its absolute-millimetre cues leak the answer to every ratio-based query that a properly designed numeric QA task would ask. **Furthermore,** ground truth across all four prior works is either parsed without re-execution (DeepCAD), filtered only by Chamfer threshold (CAD-Coder, CAD-Recode), or limited to a few hundred samples (CADPrompt) — and none use a rotation-invariant IoU, so a geometrically correct but axis-permuted solid is silently penalized.

To address these gaps, we introduce **BenchCAD**, a CAD code-generation benchmark designed around three principles: industrial-standard anchoring, operation breadth, and capability decomposition. The dataset comprises 20{,}143 procedurally-generated parts spanning 106 parametric families, with 55\% of families bound to ISO, DIN, EN, ASME, or IEC specification tables — DIN 338 twist drills, ISO 23509 bevel gears, DIN 2095 compression springs, DIN 8187 roller chains, and so on, sampled at parameter values drawn from real specification ranges, not arbitrary geometry. The CadQuery operations exercised span 45+ distinct API calls including twist-extrusion, lofting, sweeping, helical sketches, and rectangular and polar patterns — between 9$\times$ and 22$\times$ broader than prior corpora. Every record is execution-validated: the CadQuery source is re-run inside a sandbox, the resulting STEP is voxelized at 64$^3$ resolution, and a 6-orientation rotation-invariant 3D IoU against a reference solid must reach 0.99 for the record to enter the verified split. Atop this dataset we define **five evaluation tasks** — image-to-code, image-conditioned numeric QA, code-conditioned numeric QA, image-conditioned editing, and text-only editing — designed so that score *differences* across tasks isolate which rung of the parametric pyramid is the bottleneck.

Across our evaluation of 30+ frontier models, the diagnostic differential is striking. Even the strongest reasoning models — GPT-5, Claude 4.6 Opus, o3 — score 15--20 percentage points lower on image-conditioned numeric QA than on the matched code-conditioned variant; this gap survives chain-of-thought prompting, persists across the 1B-to-78B Qwen2.5-VL and InternVL3 scaling series, and is unchanged by supplying eight views instead of four. We name this systematic image-versus-code gap the **Vision Bottleneck**: the dominant remaining capability deficit in programmatic CAD is not at the code-synthesis rung but at the visual-perception rung. The Vision Bottleneck remains substantial across every architecture and inference strategy we tested, suggesting that the core challenge of reading manufacturing-grade engineering imagery is far from solved by parameter scaling, view augmentation, or naive code-finetuning alone, and that the path forward lies in training procedures explicitly aware of the parametric-symbolic structure of CAD geometry.

\paragraph{Our contributions are threefold.}
\begin{enumerate}[leftmargin=1.4em,topsep=4pt,itemsep=4pt]
  \item \textbf{The BenchCAD dataset and CadGen pipeline.} We release 20{,}143 verified parametric CAD parts spanning 106 families (55\% anchored to ISO/DIN/EN/ASME/IEC specification tables), exercising 45+ distinct CadQuery operations, and supplemented by a 433-pair instruction-guided edit subset, a 530-sample stratified Lite split for rapid leaderboards, and a 162{,}000-pair training corpus derived from GenCAD. Underlying the dataset is CadGen, a procedural construction pipeline integrating standard-table sampling, op-list emission, sandboxed execution under a 64$^3$ rotation-invariant 3D IoU $\geq 0.99$ verification, and Croissant 1.0 metadata generation; all releases are publicly hosted under \texttt{BenchCAD/cad\_bench} on Hugging Face.

  \item \textbf{The first capability-decomposed CAD code-generation benchmark.} We define five evaluation tasks — \texttt{img2cq}, \texttt{qa\_img}, \texttt{qa\_code}, \texttt{edit\_img}, and \texttt{edit\_code} — designed so that the score contrast between paired tasks directly isolates which rung of the parametric pyramid (visual reconstruction, geometric abstraction, code synthesis) is the bottleneck for a given model. Scoring is rotation-invariant under the 6-orientation cube group and scale-invariant under prompt construction (no millimetre leakage), correcting two systematic optimism sources in prior CAD evaluation protocols.

  \item \textbf{The Vision Bottleneck diagnostic.} We evaluate 30+ frontier vision-language and code-language models — including reasoning, non-reasoning, and CAD-specialised systems — and identify a systematic 15--20 point gap between code-conditioned and image-conditioned numeric QA scores that survives chain-of-thought prompting, parameter scaling from 1B to 78B in two open-source families, and view-count augmentation. This finding refocuses the CAD-LM research agenda from code-synthesis improvements (where prior work has concentrated) onto visual-to-parametric reconstruction, where BenchCAD provides the first quantitative measurement.
\end{enumerate}

---

## 4. Open notes (next pass)

- Title pick (1/2/3)? — default 1
- Vision Bottleneck 15--20 pt 数字是 placeholder,等真跑分回填
- M8 flange 例子要不要换成 helical_gear / coil_spring 等更"复杂工业件"以呼应 §3 highlight?
- 是否在 paragraph 4 末加一句"a representative subset of these tasks appears in Figure 2" → 提前 hook headline figure
- bibkey 列表统一(Wu2021/Khan2024/Guan2025/Rukhovich2025/Alrashedy2025)等 main.bib
- 是否要在 contribution 前加一个 transition 段(避免 contribution 块紧贴 finding 段)
- arXiv 预印 vs 双盲 — 影响投稿前后 release 时间线
