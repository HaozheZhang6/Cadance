# §4 Benchmark Tasks and Capability Decomposition (draft v0)

> Target ≤ 1.5 page。3 子节: 4.1 capability framework / 4.2 5 task definitions + scoring / 4.3 invariant scoring protocol

---

## 4.1 The Image$\to$Code Capability Chain

A single end-to-end metric (Chamfer distance, IoU, pass rate) on an image-to-code task reports *whether* a model succeeded, but not *which capability failed*. Prior CAD code-generation benchmarks (Text2CAD, CAD-Coder, CAD-Recode, CADCodeVerify) score one such metric per model and conflate three distinct sub-capabilities required to map a multi-view image to executable parametric source.

We decompose the image$\to$code task into three causal links (Table~\ref{tab:capability}):

\begin{itemize}[leftmargin=1.2em,topsep=2pt,itemsep=1pt]
\item $C_1$ \textbf{Visual + 3D Reconstruction} ($f_{C_1}: \text{multi-view image} \to \text{3D shape}$). The model must integrate four orthographic views into a coherent volumetric understanding.
\item $C_2$ \textbf{Geometric$\to$Parametric Abstraction} ($f_{C_2}: \text{3D shape} \to \{(p_i,v_i)\}$). The model must identify the parametric structure underlying the geometry: which dimensions are bores, which are wall thicknesses, which are ratios.
\item $C_3$ \textbf{Parametric$\to$Code Synthesis} ($f_{C_3}: \{(p_i,v_i)\} \to \text{CadQuery code}$). The model must emit syntactically valid, executable code that realises the parameters in the target API (workplane choice, op order, fillet radii, hole alignment).
\end{itemize}

BenchCAD's five tasks are designed so that each task exercises a known subset of $\{C_1, C_2, C_3\}$, and so that score *differences* across tasks isolate which capability is the bottleneck. For example, the gap between \texttt{qa\_img} and \texttt{qa\_code} scores under matched prompts measures the cost of replacing direct code access with visual perception — i.e.\ $C_1$ alone. We refer to this systematic gap as the \textbf{Vision Bottleneck}, and it is the central diagnostic finding of BenchCAD (§\ref{sec:exp_capability}).

\paragraph{Diagnostic differentials.} Given a model's per-task scores, four interpretable contrasts apply:
\begin{itemize}[leftmargin=1.2em,topsep=2pt,itemsep=1pt]
\item \texttt{qa\_img} $-$ \texttt{qa\_code} (negative) $\Rightarrow$ \emph{$C_1$ is the bottleneck}.
\item \texttt{qa\_code} (low absolute) $\Rightarrow$ \emph{$C_2$ is the bottleneck}.
\item \texttt{img2cq} $-$ \texttt{edit\_code} (negative) $\Rightarrow$ \emph{$C_3$ + full-stack composition is the bottleneck}.
\item \texttt{edit\_img} $-$ \texttt{edit\_code} (negative) $\Rightarrow$ $C_1$ cost is preserved on edit tasks.
\end{itemize}

Section~\ref{sec:exp_capability} reports these differentials across 30+ models and shows that the Vision Bottleneck is the dominant gap, exceeding scaling and reasoning gains for every model family tested.

## 4.2 Task Definitions and Scoring

\paragraph{Task 1 — \texttt{img2cq} (image-to-code).} \emph{Inputs:} four canonical orthographic views (front / right / top / iso) of a verified part, plus a fixed system prompt requesting CadQuery source. \emph{Output:} CadQuery Python code. \emph{Score:} we re-execute the generated code, voxelize the resulting STEP, and compute rotation-invariant 3D IoU against the reference solid. The headline metric is \emph{Pass\textsubscript{IoU$\geq 0.5$}}, the fraction of generations achieving IoU $\geq 0.5$ under the cube symmetry group; we additionally report mean Chamfer distance, invalidity ratio (execution-failure rate), and Feature-F1 over primitive types.

\paragraph{Task 2 — \texttt{qa\_img} (visual numeric QA).} \emph{Inputs:} the four views plus a numeric question (e.g.\ "what is the ratio of inner to outer diameter?", "how many spokes does the wheel have?"). Questions are sampled from a per-family question bank that asks only ratios and integer counts — never absolute lengths in millimetres — making them invariant to overall part scale. \emph{Output:} a single number. \emph{Score:} relative error $\leq 5\%$ for ratios; exact match for integers. Question bank construction is in Appendix~A.

\paragraph{Task 3 — \texttt{qa\_code} (code-only numeric QA).} \emph{Inputs:} the same numeric question as \texttt{qa\_img}, but conditioned on the verified CadQuery source code instead of images. This task isolates $C_2$ (parametric reasoning) from $C_1$ (visual perception); the model has perfect access to the underlying parameters and must derive the answer symbolically. \emph{Output \& Score:} same as \texttt{qa\_img}.

\paragraph{Task 4 — \texttt{edit\_img} (image-conditioned edit).} \emph{Inputs:} the four views of an original part, the original CadQuery source, and a natural-language edit instruction (\emph{"add a 3 mm chamfer on the outer top edges"}, \emph{"remove one of the four legs"}, \emph{"increase the bore diameter to 12 mm"}). The BenchCAD-Edit split provides 433 curated instruction--edit pairs across 106 families, spanning dimensional, additive, subtractive, and multi-step categories. \emph{Output:} edited code. \emph{Score:} Pass@1 = $\mathbb{1}[\text{IoU}(\text{edited}, \text{target}) \geq 0.99]$; we additionally report mean IoU.

\paragraph{Task 5 — \texttt{edit\_code} (text-only edit).} \emph{Inputs:} same as \texttt{edit\_img} but without the images. This is the text-only counterpart of \texttt{edit\_img} and isolates $C_3$ (code synthesis under natural-language guidance) without visual context. \emph{Output \& Score:} as \texttt{edit\_img}. To our knowledge BenchCAD is the first benchmark targeting instruction-guided CAD code editing as a first-class evaluation, distinct from interactive refinement loops where the system queries itself.

\paragraph{Aggregate.} The headline aggregate is the macro-mean across the five tasks (\emph{Avg}). We report per-difficulty splits in Table~\ref{tab:family_cliff}.

## 4.3 Invariance and Honesty in Scoring

Two design choices distinguish BenchCAD's scoring from prior practice.

\textbf{Rotation invariance.} A solid that is geometrically correct but axis-permuted is correct from a manufacturing standpoint — the user can re-install the workpiece in any of the cube symmetries. We compute IoU as the maximum over the 6 face-up orientations (or the full 24-element cube rotation group, configurable at evaluation time) instead of single-axis-aligned IoU. This avoids the systematic underestimation of model scores observed in CADPrompt~\cite{Alrashedy2025} where bounding-box IoU penalizes axis swaps. See Appendix~B for the implementation.

\textbf{Scale invariance.} Prompts and questions never include absolute millimetre values. A typical \texttt{qa\_img} question is \emph{"What is the ratio of bore diameter to outer diameter?"} (numerical ratio), not \emph{"What is the bore diameter in mm?"} (absolute scale). Likewise, \texttt{img2cq} prompts request "produce executable CadQuery code that reconstructs the depicted part to scale" without disclosing the part's physical size. Models that exploit absolute-scale hints are removed from comparison; an ablation in §\ref{sec:ablation} quantifies the +4.6 pt inflation that mm leakage produces on \texttt{qa\_img}, calibrating the systematic optimism of prior protocols.

---

## TODO
- Question bank construction (Appendix A) 草稿 — 我们 qa_generator 已生成,需描述 family-specific Q template + ratio/integer 比例
- Rotation IoU appendix (Appendix B) — 引用 6/24-group 实现细节,链 bench/metrics
- Edit category 实际计数 (212 dim + 58 dim-supp + 45 add + 118 multi 来自 PROGRESS) — 入正文
- "first instruction-guided CAD code editing" claim — 需双盲双扫 prior(尤其 Query2CAD / CAD-Assistant / CAD-MLLM 是否有 edit subset)
- Pass@1 IoU≥0.99 vs IoU≥0.95 阈值选择论证(too strict?too loose?)
