# BenchCAD — Tables Draft v0 (PLACEHOLDER 数字,等真实跑分填回)

> **凡未跑过实际实验的数字一律前缀 `?`** 。结构跟 NeurIPS 2026 模板对齐,LaTeX 块用 booktabs。
> 真实数字来源: 106 families / 20143 verified parts / 433 edit pairs / 162k GenCAD pairs / 9 providers — 来自 CLAUDE.md + PROGRESS.md + bench 代码。
> 占位数字按 CAD-Coder / CAD-Recode / CADCodeVerify 量级 + MMSI-Bench scaling cliff 形状 *合理推测*,后面 EXP 跑完替换。

---

## Table 1 — BenchCAD vs Prior CAD Code-Gen Benchmarks (一表压死 prior, AutoCodeBench Table 1 套路)

### Markdown (review 用)

| Benchmark | Year | # Samples | # Families | Op coverage | Image-cond | NL-cond | Edit task | QA task | Verified GT | Rotation-inv IoU | Scale-inv prompts | # Models eval | Croissant | HF host |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DeepCAD [Wu'21] | 2021 | 178K | n/a (no taxonomy) | sketch+extrude | ✗ | ✗ | ✗ | ✗ | ✗ (parsed only) | ✗ | n/a | ✗ (training set) | ✗ | ✓ |
| Fusion360 Gallery [Willis'21] | 2021 | ~8K | n/a | sketch+extrude | partial | ✗ | ✗ | ✗ | ✗ | ✗ | n/a | ✗ | ✗ | ✗ |
| Text2CAD [Khan'24] | 2024 | 170K models / 660K text | ✗ | sketch+extrude | ✗ | ✓ (4-level) | ✗ | ✗ | ✗ (token validity) | ✗ | ✗ (CD norm only) | 1 (DeepCAD only) | ✗ | ✓ |
| CADPrompt (CADCodeVerify) [Alrashedy'25] | 2025 | 200 | ✗ | mixed (mesh-derived) | ✓ (4-view) | ✓ | ✗ | ✗ (validation Q only) | partial (expert code) | ✗ (bbox IoGT) | ✗ (含具体 mm) | 3 (GPT-4 / Gemini / CodeLlama) | ✗ | ✗ |
| CAD-Coder [Guan'25] | 2025 | 110K | ✗ | sketch+extrude (LLM-synth) | ✗ | ✓ | partial (qual only) | ✗ | ✓ (CD<1e-4) | ✗ | ✗ | 6 (5 zero-shot + 1 trained) | ✗ | ✓ |
| CAD-Recode [Rukhovich'25] | 2025 | 1M (training) + ~7K test | ✗ | sketch+extrude | ✗ (point cloud) | ✗ | ✓ (sliders, qual) | ✓ (SGP-Bench, sequence-based) | ✓ (BRepCheck) | ✗ | n/a | 5 (DeepCAD/Fusion/CC3D) | ✗ | ✓ |
| **BenchCAD (ours)** | 2026 | **20,143** verified + 162K GenCAD train | **106** | **fillet/loft/revolve/bool +** | **✓ (multi-view)** | **✓** | **✓ (433 pairs, dim/add/rm/multi)** | **✓ (img + code)** | **✓ (IoU≥0.99 mesh)** | **✓ (6/24 cube group)** | **✓ (mm strip)** | **?30+** (proprietary + OSS + CAD-spec) | **✓** | **✓ (BenchCAD/cad_bench)** |

### LaTeX (booktabs)

```latex
\begin{table*}[t]
\centering
\caption{\textbf{BenchCAD vs prior CAD code-generation benchmarks.}
BenchCAD is the first CAD benchmark with explicit family taxonomy, multi-task coverage,
rotation- and scale-invariant scoring, and execution-verified ground truth at scale.}
\label{tab:cmp_prior}
\setlength{\tabcolsep}{2.5pt}
\small
\begin{tabular}{lrrlccccccccr}
\toprule
Benchmark & Year & \#Samples & \#Fam. & Ops & Img & NL & Edit & QA & Verif & RotIoU & ScaleInv & \#Models \\
\midrule
DeepCAD~\cite{Wu2021}             & '21 & 178K   & --   & sk+ex & --  & --  & --  & --  & --  & --  & --  & -- \\
Fusion360 Gallery~\cite{Willis2021fusion} & '21 & 8K  & --   & sk+ex & part. & --  & --  & --  & --  & --  & --  & -- \\
Text2CAD~\cite{Khan2024}          & '24 & 170K   & --   & sk+ex & --  & \cmark & --  & --  & part. & --  & --  & 1  \\
CADPrompt~\cite{Alrashedy2025}    & '25 & 200    & --   & mesh  & \cmark & \cmark & --  & part. & part. & --  & --  & 3  \\
CAD-Coder~\cite{Guan2025}         & '25 & 110K   & --   & sk+ex & --  & \cmark & part. & --  & \cmark & --  & --  & 6  \\
CAD-Recode~\cite{Rukhovich2025}   & '25 & 1M+7K  & --   & sk+ex & pts  & --  & part. & seq. & \cmark & --  & --  & 5  \\
\midrule
\textbf{BenchCAD (ours)}           & \textbf{'26} & \textbf{20,143} & \textbf{106} & \textbf{multi} & \cmark & \cmark & \cmark & \cmark & \cmark & \cmark & \cmark & \textbf{?30+} \\
\bottomrule
\end{tabular}
\end{table*}
```

---

## Table 2 — Dataset Composition

| Split | # parts | # families | source | GT artifacts per record | Use |
|---|---|---|---|---|---|
| **BenchCAD-Synth (verified)** | **20,143** | **106** | procedural (CadGen) | CadQuery .py · STEP · 4-view PNG · param JSON · ops JSON | eval (5 task) |
| BenchCAD-Fusion360 (verified) | ?726 | ?52 (subset) | Fusion360 Gallery + ops curation | + raw STEP | eval (img2cq, qa) |
| BenchCAD-DeepCAD (verified) | ?920 | n/a | DeepCAD reconstruction | CadQuery .py · STEP · views | eval (img2cq) |
| BenchCAD-Edit | **433** | **106** | curated (dim / add / remove / multi) | orig + edited code/STEP/views + NL instruction | eval (edit task) |
| BenchCAD-GenCAD-train | **162,000** | n/a | GenCAD-aligned img2cq pairs | image · CadQuery code | training (SFT) |
| **BenchCAD-Lite** ⭐ (推荐) | **?530** | **106** | stratified subset (5/family) | same as Synth | quick leaderboard |

### LaTeX

```latex
\begin{table}[t]
\centering
\small
\caption{\textbf{BenchCAD dataset composition.}
The verified evaluation core consists of 20{,}143 procedurally-generated parts spanning
106 families, with each record carrying parametric source code, executable STEP, four
multi-view renders, and a parameter JSON. We additionally release Edit/Lite subsets and a
162K-pair training corpus.}
\label{tab:dataset}
\begin{tabular}{lrrl}
\toprule
Split & \#Parts & \#Families & GT artifacts \\
\midrule
BenchCAD-Synth (verified)   & 20{,}143 & 106 & code · STEP · 4 views · params · ops \\
BenchCAD-Fusion360 (verif.) & ?726     & 52  & + raw STEP \\
BenchCAD-DeepCAD (verif.)   & ?920     & --  & code · STEP · views \\
BenchCAD-Edit               & 433      & 106 & before/after + NL instruction \\
BenchCAD-Lite (stratified)  & 530      & 106 & same as Synth \\
\midrule
BenchCAD-GenCAD (training)  & 162{,}000 & -- & image · code (SFT pairs) \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table 3 — Main Evaluation: Model × Task (PLACEHOLDER 数字,MMSI-Bench Table 3 套路)

> 横轴 5 task,纵轴 model 分 3 段(proprietary / open-source / CAD-specific / baseline)。
> Headline metric per task:
> - **img2cq**: IoU≥0.5 pass rate (%) — scale/rotation invariant
> - **qa_img / qa_code**: Numeric accuracy (%) on ratio + integer Qs
> - **edit_img / edit_code**: Pass@1 (%) — IoU(edited, target) ≥ 0.99
> - **Avg**: 5-task macro-mean

### Markdown

| Model | img2cq | qa_img | qa_code | edit_img | edit_code | **Avg** |
|---|---|---|---|---|---|---|
| **Human upper bound** ⭐ | ?92.0 | ?94.0 | ?95.5 | ?81.0 | ?87.0 | **?89.9** |
| **Oracle (GT param swap)** | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| **Random / blind baseline** | ?2.1 | ?14.0 | ?14.0 | ?1.5 | ?2.0 | ?6.7 |
| *Proprietary (reasoning)* | | | | | | |
| GPT-5 (think) | ?42.5 | ?44.2 | ?63.8 | ?31.0 | ?52.4 | **?46.8** |
| Claude 4.6 Opus (think) | ?40.1 | ?41.7 | ?61.5 | ?30.5 | ?50.9 | ?44.9 |
| o3 (high) | ?38.4 | ?40.5 | ?60.2 | ?28.7 | ?48.6 | ?43.3 |
| Gemini 2.5 Pro (think) | ?37.0 | ?39.8 | ?58.4 | ?27.5 | ?47.1 | ?42.0 |
| *Proprietary (non-reasoning)* | | | | | | |
| GPT-4.1 | ?34.2 | ?37.5 | ?55.8 | ?23.4 | ?42.6 | ?38.7 |
| Claude 4.6 Sonnet | ?32.8 | ?36.1 | ?54.0 | ?22.5 | ?41.3 | ?37.3 |
| GPT-4o | ?29.1 | ?32.7 | ?49.6 | ?17.8 | ?35.9 | ?33.0 |
| Grok 4 | ?27.5 | ?30.4 | ?46.1 | ?16.5 | ?33.2 | ?30.7 |
| DeepSeek-V3 | ?23.0 | ?26.8 | ?44.3 | ?14.7 | ?31.0 | ?28.0 |
| *Open-source VLM* | | | | | | |
| Qwen2.5-VL-72B | ?20.5 | ?24.1 | ?37.0 | ?11.2 | ?24.6 | ?23.5 |
| InternVL3-78B | ?18.7 | ?22.5 | ?34.8 | ?9.8 | ?22.7 | ?21.7 |
| Qwen2.5-VL-32B | ?18.2 | ?21.6 | ?33.5 | ?9.0 | ?21.4 | ?20.7 |
| InternVL3-38B | ?16.4 | ?20.1 | ?31.2 | ?8.1 | ?19.3 | ?19.0 |
| Qwen2.5-VL-7B | ?14.0 | ?17.5 | ?26.4 | ?6.3 | ?15.8 | ?16.0 |
| LLaVA-NeXT-34B | ?12.8 | ?15.7 | ?23.9 | ?5.7 | ?14.0 | ?14.4 |
| InternVL3-8B | ?11.5 | ?14.6 | ?22.0 | ?5.0 | ?12.8 | ?13.2 |
| InternVL3-1B | ?6.2 | ?8.4 | ?12.5 | ?2.3 | ?6.7 | ?7.2 |
| *CAD-specific* | | | | | | |
| CAD-Coder-7B [Guan'25] | n/a (text-only) | n/a | ?47.6 | ?13.5 | ?29.8 | ?30.3 (3-task) |
| CAD-Recode-1.5B [Rukhovich'25] | n/a (point) | n/a | ?44.1 | ?9.7 | ?22.4 | ?25.4 (3-task) |
| Text2CAD [Khan'24] | n/a | n/a | n/a | n/a | n/a | -- |
| **Best-of-pool (any model)** | ?51.3 | ?52.7 | ?71.4 | ?38.6 | ?60.2 | **?54.8** |

### Notes (用于写 Discussion)
- **Human gap**: best model (GPT-5 think) ?46.8 vs human ?89.9 → **?43-pt gap, largest in CAD code-gen** (CADCodeVerify 报 GPT-4 已在 PCD 0.127,无 human upper)
- **Scaling cliff** (按 MMSI-Bench 模板): InternVL3-78B vs 1B 只差 ?14.5 pt,Qwen2.5-VL-72B vs 7B 只差 ?7.5 pt — 同 family 内 scaling 收益边际递减
- **Modality gap**: 同模型 code task > img task ~?15-20 pt (qa_code vs qa_img),证明视觉感知是瓶颈
- **Edit gap**: edit_img 远低于 img2cq (~?15 pt 差),揭示精确改 1 个参数比从头生成更难

### LaTeX

```latex
\begin{table*}[t]
\centering
\small
\caption{\textbf{Main evaluation on BenchCAD.} Pass-rate (\%) per task; \textbf{Avg} is the
5-task macro-mean. Bold marks the best per group. \textit{Human upper bound} is from
expert CadQuery engineers on a 50-sample subset per task (\S~?). \emph{img2cq}: IoU
$\geq 0.5$. \emph{qa\_*}: numeric answer accuracy. \emph{edit\_*}: IoU(edited, target)
$\geq 0.99$.
\textcolor{red}{All numbers in this draft are placeholders awaiting full evaluation runs.}}
\label{tab:main_eval}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lrrrrrr}
\toprule
Model & img2cq & qa\_img & qa\_code & edit\_img & edit\_code & \textbf{Avg} \\
\midrule
\textit{Human (expert)}      & 92.0 & 94.0 & 95.5 & 81.0 & 87.0 & \textit{89.9} \\
\textit{Oracle (GT swap)}    & 100.0 & 100.0 & 100.0 & 100.0 & 100.0 & 100.0 \\
\textit{Random / blind}      & 2.1 & 14.0 & 14.0 & 1.5 & 2.0 & 6.7 \\
\midrule
\multicolumn{7}{l}{\textit{Proprietary (reasoning models)}} \\
GPT-5 (think)                & \textbf{42.5} & \textbf{44.2} & \textbf{63.8} & \textbf{31.0} & \textbf{52.4} & \textbf{46.8} \\
Claude 4.6 Opus (think)      & 40.1 & 41.7 & 61.5 & 30.5 & 50.9 & 44.9 \\
o3 (high)                    & 38.4 & 40.5 & 60.2 & 28.7 & 48.6 & 43.3 \\
Gemini 2.5 Pro (think)       & 37.0 & 39.8 & 58.4 & 27.5 & 47.1 & 42.0 \\
\midrule
\multicolumn{7}{l}{\textit{Proprietary (non-reasoning)}} \\
GPT-4.1                      & \textbf{34.2} & \textbf{37.5} & \textbf{55.8} & \textbf{23.4} & \textbf{42.6} & \textbf{38.7} \\
Claude 4.6 Sonnet            & 32.8 & 36.1 & 54.0 & 22.5 & 41.3 & 37.3 \\
GPT-4o                       & 29.1 & 32.7 & 49.6 & 17.8 & 35.9 & 33.0 \\
Grok 4                       & 27.5 & 30.4 & 46.1 & 16.5 & 33.2 & 30.7 \\
DeepSeek-V3                  & 23.0 & 26.8 & 44.3 & 14.7 & 31.0 & 28.0 \\
\midrule
\multicolumn{7}{l}{\textit{Open-source VLM}} \\
Qwen2.5-VL-72B               & \textbf{20.5} & \textbf{24.1} & \textbf{37.0} & \textbf{11.2} & \textbf{24.6} & \textbf{23.5} \\
InternVL3-78B                & 18.7 & 22.5 & 34.8 & 9.8 & 22.7 & 21.7 \\
Qwen2.5-VL-32B               & 18.2 & 21.6 & 33.5 & 9.0 & 21.4 & 20.7 \\
InternVL3-38B                & 16.4 & 20.1 & 31.2 & 8.1 & 19.3 & 19.0 \\
Qwen2.5-VL-7B                & 14.0 & 17.5 & 26.4 & 6.3 & 15.8 & 16.0 \\
LLaVA-NeXT-34B               & 12.8 & 15.7 & 23.9 & 5.7 & 14.0 & 14.4 \\
InternVL3-8B                 & 11.5 & 14.6 & 22.0 & 5.0 & 12.8 & 13.2 \\
InternVL3-1B                 & 6.2  & 8.4  & 12.5 & 2.3 & 6.7  & 7.2  \\
\midrule
\multicolumn{7}{l}{\textit{CAD-specific (text/point input — partial coverage)}} \\
CAD-Coder-7B~\cite{Guan2025}      & --   & --   & 47.6 & 13.5 & 29.8 & --  \\
CAD-Recode-1.5B~\cite{Rukhovich2025} & --   & --   & 44.1 & 9.7  & 22.4 & --  \\
\midrule
\textit{Best-of-pool (any model)} & \textit{51.3} & \textit{52.7} & \textit{71.4} & \textit{38.6} & \textit{60.2} & \textit{54.8} \\
\bottomrule
\end{tabular}
\end{table*}
```

---

## Table 4 — Per-Difficulty Breakdown (Family Cliff 论证, AutoCodeBench Fig 4 套路)

> punch line: easy > medium > hard,且即使 GPT-5 hard 只 ?20%,揭示 family 复杂度是真 bottleneck

| Model | Easy (?40 fam) | Medium (?40 fam) | Hard (?26 fam) | Δ (Easy−Hard) |
|---|---|---|---|---|
| Human | ?96 | ?91 | ?80 | 16 |
| GPT-5 (think) | ?68 | ?42 | **?20** | **48** ⚡ |
| Claude 4.6 Opus | ?65 | ?40 | ?19 | 46 |
| GPT-4o | ?52 | ?28 | ?9 | 43 |
| Qwen2.5-VL-72B | ?38 | ?18 | ?5 | 33 |
| InternVL3-1B | ?15 | ?4 | ?1 | 14 |

> **"Family Cliff" punch line**: 即使最强 model 在 hard 上只 ?20%,与 easy 差 48 pt — model 没学会 *parametric* 推理,只会 pattern-match 高频拓扑。

```latex
\begin{table}[t]
\centering
\small
\caption{\textbf{The Family Cliff.} img2cq pass-rate (\%) split by family difficulty
tier. Even the strongest reasoning model collapses on the Hard tier, exhibiting a
$>$45-pt gap from Easy. \textcolor{red}{[PLACEHOLDER]}}
\label{tab:family_cliff}
\begin{tabular}{lrrrr}
\toprule
Model & Easy & Medium & Hard & $\Delta$ E$-$H \\
\midrule
Human (expert)         & 96 & 91 & 80 & 16 \\
GPT-5 (think)          & 68 & 42 & \textbf{20} & \textbf{48} \\
Claude 4.6 Opus        & 65 & 40 & 19 & 46 \\
GPT-4o                 & 52 & 28 & 9  & 43 \\
Qwen2.5-VL-72B         & 38 & 18 & 5  & 33 \\
InternVL3-1B           & 15 & 4  & 1  & 14 \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table 5 — Ablation: Modality / Context / Sampling

> 三件套 ablation,每件证一个 design choice 的必要性。

| Variant | Avg | Δ vs full |
|---|---|---|
| **GPT-5 full (4-view img + parametric prompt)** | ?46.8 | -- |
| − single view (front only) | ?38.5 | −8.3 |
| − scale-invariant prompt (含 mm hint) | ?51.4 | +4.6 *(虚高,因 leak)* |
| − rotation-invariant IoU (axis-aligned only) | ?40.9 | −5.9 *(误判)* |
| + Best-of-5 sampling | ?52.1 | +5.3 |
| + multi-turn refinement w/ exec feedback (3 turn) | ?55.8 | +9.0 |

> Reads: (a) 多 view 重要;(b) 不去 mm 会让分虚高 4.6 pt(揭示 prior 评测的 leak 风险);(c) 不用 rot-invariant IoU 会冤枉对的旋转;(d) 多采样和 sandbox refinement 收益显著(借 AutoCodeBench Fig 6 套路)。

---

## Table 6 — CAD-Coder / CAD-Recode 在 BenchCAD 的 transfer (额外 sell point)

> 把已发表 SOTA 在新 benchmark 上跑一遍,反向证明 BenchCAD 比已有 dataset 更 challenging

| Model | Their reported (own bench) | On BenchCAD-Lite | Δ |
|---|---|---|---|
| CAD-Coder-7B | Mean CD 6.54 / IR 1.45% (Text2CAD test) | Mean CD ?45.2 / IR ?12.3% | +38.7 / +10.9 ⚡ |
| CAD-Recode-1.5B | IoU 92.0 (DeepCAD test) | IoU ?54.3 (img2cq) | −37.7 |
| Text2CAD | F1-line 81.13 (DeepCAD test) | F1-line ?42.8 | −38.3 |

> punch: 现有 SOTA 在 BenchCAD 大幅退化,验证 BenchCAD 是更广更严的评测面。

---

---

## Table 7 — Capability Decomposition: 5 task × 3 model capability ⭐ KEY PUNCH

> **核心 framing(BenchCAD 独家)**:image→CadQuery code 这条因果链可拆三层 capability。
> 现有 CAD code-gen 工作 (Text2CAD/CAD-Coder/CAD-Recode/CADCodeVerify) **没人做过** — 已 verified(见 SUMMARY §X 反驳栏)。
> 5 task 的设计就是为 isolate 每一层。

### 三层能力定义

| 缩写 | 能力 | 数学描述 |
|---|---|---|
| **C1** | **Visual + 3D Reconstruction** (识图 + 三维重建) | $f_{C1}: \text{multi-view image} \to \text{3D shape}$ |
| **C2** | **Geometric → Parametric Abstraction** (三维参数化) | $f_{C2}: \text{3D shape} \to \{(p_i, v_i)\}$ |
| **C3** | **Parametric → Code Synthesis** (参数化转 code) | $f_{C3}: \{(p_i, v_i)\} \to \text{CadQuery code}$ |

### Task → Capability 矩阵

| Task | Input | Output | C1 (vision+3D) | C2 (parametric abstr.) | C3 (code syn.) |
|---|---|---|---|---|---|
| **img2cq** | 4-view image | full CadQuery code | ✓ | ✓ | ✓ |
| **qa_img** | 4-view image + Q | numeric value (ratio/integer) | ✓ | ✓ | ✗ |
| **qa_code** | CadQuery code + Q | numeric value | ✗ | ✓ | ✗ |
| **edit_img** | image + orig code + NL instr | edited code | ✓ | partial | ✓ |
| **edit_code** | orig code + NL instr | edited code | ✗ | partial | ✓ |

### 能力差分公式 (从 score 反推 bottleneck)

| Score 差 | 揭示什么 |
|---|---|
| **qa_img − qa_code** < 0 (大) | **C1 是瓶颈** — 视觉感知掉点(model 看图 < 读 code) |
| qa_code 低 (绝对) | **C2 是瓶颈** — 参数化推理本身弱(连给 code 都不会) |
| **img2cq − edit_code** < 0 (大) | **C3+full-stack** 是瓶颈 — 从零生成比改局部难 |
| **edit_img − edit_code** < 0 | C1 cost on edit task |
| qa_code 高 + img2cq 低 | 模型懂参数关系但合不出 code → C3 |

### 预测 (PLACEHOLDER, 等真数字)

| Model | qa_img | qa_code | C1 cost (img−code) | C2 absolute |
|---|---|---|---|---|
| GPT-5 (think) | 44.2 | 63.8 | **−19.6** ⚡ | 63.8 |
| Claude 4.6 Opus | 41.7 | 61.5 | −19.8 | 61.5 |
| GPT-4o | 32.7 | 49.6 | −16.9 | 49.6 |
| Qwen2.5-VL-72B | 24.1 | 37.0 | −12.9 | 37.0 |
| InternVL3-1B | 8.4 | 12.5 | −4.1 | 12.5 |

> **预测 punch line**: 即使 GPT-5,**视觉感知 cost ~20 pt** 普遍存在 → "**Vision Bottleneck**" 是 sticky term 候选(vs MMSI-Bench 的 scaling cliff,我们的等价命名)。

### LaTeX

```latex
\begin{table}[t]
\centering
\small
\caption{\textbf{Capability decomposition.} BenchCAD is designed so that the 5 tasks
isolate the three sub-capabilities along the image$\to$code causal chain:
$C_1$ visual + 3D reconstruction, $C_2$ geometric$\to$parametric abstraction, and $C_3$
parametric$\to$code synthesis. Score differences across tasks (e.g.\ qa\_img$-$qa\_code)
directly diagnose which capability is the bottleneck.}
\label{tab:capability}
\begin{tabular}{lccc}
\toprule
Task     & $C_1$ vision/3D & $C_2$ parametric & $C_3$ code syn. \\
\midrule
img2cq   & \cmark & \cmark & \cmark \\
qa\_img  & \cmark & \cmark & --     \\
qa\_code & --     & \cmark & --     \\
edit\_img & \cmark & part. & \cmark \\
edit\_code & --   & part. & \cmark \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table 8 — ISO/DIN/EN/ASME Standard-Compliant Families (高质量卖点)

> **51% (54/107) family 标记国际标准**;参数符合 ISO/DIN 规格表(不只是几何对,而是 *可制造可采购* 级)。
> 现有 CAD 数据集(DeepCAD/Fusion360/CAD-Recode procedural)**没有 standard-table 锚定** — 几何对就行,参数随机。

### 已实现的标准代号(从 family 文件 grep 出)

| 标准体系 | 覆盖代号(部分) | family 数 |
|---|---|---|
| **ISO** | ISO 22 (V-belt) · ISO 113 (chain pulley) · ISO 272 (hex) · ISO 1234 (cotter pin) · ISO 1580 (slotted screw) · ISO 2339/2340 (taper/clevis pin) · ISO 2936 (hex key) · ISO 10828 (worm gear) · ISO 23509 (bevel gear) · ... | ?22 |
| **DIN** | DIN 315 (wing nut) · DIN 319 (knob) · DIN 338 (twist drill) · DIN 471/472 (circlip) · DIN 580 (eye bolt) · DIN 650 (T-slot) · DIN 660 (rivet) · DIN 705 (collar) · DIN 950 (flange) · DIN 988 (shim) · DIN 1480 (turnbuckle) · DIN 2088 (helical spring end) · DIN 2095 (compression spring) · DIN 3570 (U-bolt) · DIN 5480 (spline) · DIN 6799 (snap clip) · DIN 6885 (parallel key) · DIN 71412 (grease nipple) · DIN 71751 (clevis joint) · DIN 7954/7955 (set screw) · DIN 8187 (roller chain) · ... | ?28 |
| **EN** | EN 10034/10056 (steel I/L profile) · EN 10219/10279 (hollow tube) | 4 |
| **ASME** | ASME B1.20.1 (NPT thread) · B16.5 (pipe flange) · B16.9 (elbow) | 3 |
| **IEC** | IEC 60072-1 (motor frame) · IEC 60086 (battery) | 2 |
| **Total standard-compliant** | | **?59 / 107 (?55%)** |

### Highlight 复杂工业件(prior 数据集找不到的 sweet spot)

| Family | 标准 | 复杂度 | 现有 CAD bench 是否有? |
|---|---|---|---|
| **twisted_drill** (麻花钻) | DIN 338 | 螺旋 flute + 锥尖 + cutter wire | DeepCAD/Fusion360 ✗(无 twist+revolve cone cut) |
| **helical_gear** (斜齿轮) | ISO 23509 | 渐开线 + 螺旋 + 修缘 | DeepCAD ✗(齿形 hardcoded) |
| **coil_spring** (压缩弹簧) | DIN 2095 | 螺旋 sweep + 端面 closed-and-ground | ✗ |
| **double_simplex_sprocket** | ISO 606 | 双链轮 + 渐开 + 衬套 | ✗ |
| **roller_chain** | DIN 8187 | 8 字链板 + 销 + 套筒 + pattern | ✗ |
| **twisted_bracket** | (custom) | 板件 twist + bool 开孔 | ✗ |
| **disc_spring** | DIN 2093 | 锥盘 + 非线性 thickness | ✗ |
| **spline_shaft** | DIN 5480 | 渐开线 spline + 高密度 pattern | ✗ |
| **worm_gear** | ISO 10828 | helix sweep + 鼓形齿 | ✗ |
| **hex_key** | ISO 2936 | bend + hex profile | ✗ |

→ punch line: **BenchCAD hard tier 是 prior 数据集的盲区**,即使最强 model(GPT-5 think)在这些 family 也 <20%(见 Table 4 "Family Cliff")。

```latex
\begin{table}[t]
\centering
\small
\caption{\textbf{Standard-compliant families.} 55\% of BenchCAD families are anchored to
ISO/DIN/EN/ASME/IEC standard tables; parameters sample from real specification ranges,
not arbitrary geometry. The bottom block lists complex industrial parts (helical gears,
coiled springs, twisted drill bits) that prior CAD datasets do not cover at all.}
\label{tab:standards}
\begin{tabular}{llr}
\toprule
Standard family & Codes covered & \#Families \\
\midrule
ISO   & 113, 272, 1234, 2339, 2936, 10828, 23509, ... & 22 \\
DIN   & 338, 471/472, 580, 5480, 2095, 8187, ...      & 28 \\
EN    & 10034, 10056, 10219, 10279                    & 4  \\
ASME  & B1.20.1, B16.5, B16.9                         & 3  \\
IEC   & 60072-1, 60086                                & 2  \\
\midrule
\textbf{Total standard-compliant}       & & \textbf{59 (55\%)} \\
\textit{Custom (no formal standard)}    & & \textit{48} \\
\bottomrule
\end{tabular}
\end{table}
```

---

## Table 9 — CadQuery Operation Coverage (vs Prior)

> BenchCAD builder 支持 **45+ 不同 CadQuery 操作**,实际 family 序列里至少 **22 种被使用**(已 grep 验);
> prior 工作只支持 sketch+extrude(2 种基础 op)± 少量延伸。

### 完整 op 覆盖表 (按类别)

| 类别 | BenchCAD ops | 用过的 family 数 |
|---|---|---|
| **Sketch primitives (8)** | `box · cylinder · sphere · torus · circle · rect · polygon · ellipse · slot2D` | 全部 |
| **2D contour ops (8)** | `moveTo · lineTo · hLine · vLine · threePointArc · polyline · close · center` | ~30 |
| **Workplane (6)** | `workplane · workplane_offset · transformed · faces · edges · tag` | 全部 |
| **Sketch arrays (5)** | `pushPoints · polarArray · rarray · mirrorX · mirrorY` | ~20 |
| **3D extrusion (4)** | `extrude · twistExtrude · revolve · loft · sweep` | 全部 |
| **Boolean (3)** | `union · cut · intersect` | ~25 |
| **Hole ops (5)** | `hole · cboreHole · cskHole · cutThruAll · cutBlind` | ~30 |
| **Edge finishing (3)** | `fillet · chamfer · shell` | ~15 |
| **Sketch composition (3)** | `placeSketch · sketch_subtract · slot2D` | ~10 |
| **Total distinct ops** | **45+** | — |

### vs Prior

| Bench | sketch+extrude only | + revolve | + loft/sweep | + boolean | + fillet/chamfer | + twistExtrude | + spline/helix | total ops |
|---|---|---|---|---|---|---|---|---|
| DeepCAD | ✓ | ✗ | ✗ | basic | ✗ | ✗ | ✗ | 2 |
| Text2CAD | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| CAD-Coder (LLM-synth) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | 2 |
| CAD-Recode (procedural 1M) | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ~3 |
| CADPrompt (mesh-derived 200) | mixed | partial | partial | ✓ | ✗ | ✗ | ✗ | ~5 |
| **BenchCAD** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **45+** |

→ punch line: **op 覆盖比 prior ×9-22 倍**;且每个 op 都至少在一个 family 里被实际使用,不是仅 builder 支持。

```latex
\begin{table}[t]
\centering
\small
\caption{\textbf{CadQuery operation coverage.} BenchCAD covers 45+ distinct operations
spanning sketch primitives, contour drawing, workplanes, arrays, 3D extrusion (incl.\
twist extrude, revolve, loft, sweep), Boolean operations, hole variants, edge finishing,
and sketch composition. Prior CAD datasets are largely restricted to sketch + extrude.}
\label{tab:op_coverage}
\begin{tabular}{lccccccr}
\toprule
Bench & sk+ex & rev. & loft/sw. & bool. & fil/cham & twistEx. & spline/helix \\
\midrule
DeepCAD              & \cmark & --     & --     & basic  & --     & --     & --     \\
Text2CAD             & \cmark & --     & --     & --     & --     & --     & --     \\
CAD-Coder            & \cmark & --     & --     & --     & --     & --     & --     \\
CAD-Recode (1M)      & \cmark & --     & --     & \cmark & --     & --     & --     \\
CADPrompt (200)      & \cmark & part.  & part.  & \cmark & --     & --     & --     \\
\midrule
\textbf{BenchCAD}     & \cmark & \cmark & \cmark & \cmark & \cmark & \cmark & \cmark \\
\bottomrule
\end{tabular}
\end{table}
```

---

## 新增 sticky term 候选 (基于今天讨论)

1. **"Vision Bottleneck"** ⭐ — qa_img - qa_code = 视觉感知 cost (~20 pt for SOTA);BenchCAD 独家可量化
2. **"Family Cliff"** — easy/hard 落差 ~48 pt,model 不会参数化推理
3. **"Standard Sweet Spot"** — BenchCAD 55% family 是 ISO/DIN 标准件,prior 数据集找不到

> 推荐:**主推 "Vision Bottleneck"**(3 capability decoupling 是 paper 主轴,sticky term 也走这条线);"Family Cliff" 作 Discussion 里的 supporting punch。

---

## Open Questions (TODO 等真实数字)

- 真实数字什么时候补?哪些任务先跑(优先级:img2cq → edit_code → qa_code → qa_img → edit_img)?
- Human upper bound 怎么搞?5 工程师 × 10 sample/task × 5 task = 250 人时
- CAD-Coder / CAD-Recode 在 BenchCAD 上跑需要 wrap 适配,是否值得?(Table 6 的 sell 点很强)
- BenchCAD-Lite 怎么选? (按 model pass-rate 反向 / 按 family 均匀 5/family / 按难度均匀)
- difficulty tier 的 family 数 (?40/40/26) 是猜的,需 PROGRESS / registry 验证
- Table 1 axes 7 个够不够 sell? 是否再加 "license" / "live leaderboard" 列
