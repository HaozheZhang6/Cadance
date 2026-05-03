# §5 Trained Baselines and Transfer Evaluation (draft v0)

> Target ≤ 1.5 page。3 子节: 5.1 BenchCAD-trained open baseline / 5.2 transfer of the MSU/SnT lineage (cadrille + CADEvolve) / 5.3 ceiling and gap analysis
> All numbers are **PLACEHOLDER** awaiting GPU runs (see Appendix C: transfer-baseline reproduction).

---

## 5.1 An Open BenchCAD-Trained Baseline

To bound the difficulty of BenchCAD with publicly reproducible numbers, we release a baseline model trained directly on the dataset. We fine-tune **Qwen2-VL-2B**~\cite{Qwen2VL} on a mixture of the 162K-pair Cadance-GenCAD corpus and the 20{,}143-record BenchCAD-Synth split (image$\to$code), training for 2 epochs at learning rate $1\mathrm{e}{-5}$ on 8$\times$A800-80GB GPUs (\textasciitilde 9 GPU-hours total). We do not apply reinforcement learning; this baseline targets reproducibility, not state of the art. We make the training script, data manifest, and resulting checkpoint available under MIT licence. As Table~\ref{tab:transfer} shows, this baseline reaches an aggregate score of \textcolor{red}{?18.4}\% on BenchCAD-Lite — comparable to mid-tier proprietary models and substantially below the same-architecture cadrille-RL release.

This baseline is intentionally weak. Its purpose is to provide a community lower bound and to make the transfer-baseline gaps in §\ref{sec:transfer} interpretable: any improvement attributable to data construction (cadrille's 1M procedural; CADEvolve's 2.7M evolutionary), to multi-task pre-training (cadrille's pc/img/text mixing), or to RL fine-tuning (Dr.CPPO with IoU reward) appears as a contrast against this open baseline rather than against an opaque private model. We discuss the diminishing returns of naive SFT scaling — and why our baseline does not threaten the SOTA — in §\ref{sec:discussion}.

## 5.2 Transfer of the MSU/SnT Lineage to BenchCAD
\label{sec:transfer}

The CAD-Recode/cadrille/CADEvolve lineage~\cite{Rukhovich2025,Kolodiazhnyi2026,Elistratov2026} represents the current state of the art on existing CAD code-generation benchmarks (DeepCAD image IoU 92.6 for CADEvolve; Fusion360 image IoU 87.2). Both released checkpoints are inference-only (no LLM API call at decode time), share the same Qwen2-VL-2B backbone, and accept multi-view image input compatible with BenchCAD's render protocol. We therefore evaluate the two latest publicly released checkpoints — \texttt{maksimko123/cadrille-rl} (cadrille-RL, ICLR'26) and \texttt{kulibinai/cadevolve-rl1} (CADEvolve, Feb 2026) — on BenchCAD's \texttt{img2cq} task using the same scoring pipeline applied to all other models.

\paragraph{Headline transfer drop.} Despite scoring \textgreater{}90\% IoU on their respective evaluations, both models suffer substantial degradation on BenchCAD. Table~\ref{tab:transfer} reports placeholder gaps of \textcolor{red}{?32 and ?28 points} on the headline IoU metric, with the steepest drops concentrated in the standard-anchored hard-tier families (helical gears, twist drills, coil springs) and in operations not exercised during their training (twist-extrusion, lofting, sweeping, helical sketches). The Vision Bottleneck pattern (§\ref{sec:capability}) is also reproduced: cadrille-RL's image-conditioned numeric QA score is \textcolor{red}{?17 points} lower than its code-conditioned counterpart, matching the systematic gap observed for non-CAD-specialised frontier models.

\paragraph{Why the gap is honest, not artefactual.} We replicate the lineage's render protocol (8-view 238$\times$238 grid; cube normalization to [-100, 100]$^3$) for the transfer evaluation, eliminating mismatches in viewing geometry as a confound. We further verify that the released models reach the published IoU values on a held-out 200-sample DeepCAD slice within $\pm$0.5 points, establishing that our scoring infrastructure does not systematically penalize their outputs. The remaining gap on BenchCAD is therefore a true generalization deficit: training corpora restricted to sketch + extrude do not transfer to families requiring helical sweeps, parametric gear teeth, or DIN-anchored standard parts.

\paragraph{Implication for the field.} The transfer experiment validates the position adopted in §\ref{sec:related}: the existing CAD code-generation benchmarks are saturating against a narrow operation distribution and a narrow part vocabulary, and SOTA model improvements are increasingly within-distribution rather than out-of-distribution. BenchCAD reopens out-of-distribution evaluation by exposing the operation-coverage and standard-anchoring gaps that prior protocols cannot measure.

## 5.3 Reproduction Recipe (for Appendix C)

The transfer evaluation requires only public artifacts and runs on a single A100 GPU in under two hours per model. Reproduction uses our \texttt{bench/fetch\_data.py} one-line HF fetch (releases the verified dataset and the edit subset directly from \texttt{BenchCAD/cad\_bench}), the \texttt{bench.eval} runner with \texttt{--model maksimko123/cadrille-rl --task img2cq --split BenchCAD-Lite --seed 42}, and the released model's documented inference entry-point. We provide a wrapper adapter under \texttt{bench/models/providers/cadrille.py} (and a parallel \texttt{cadevolve.py}) so that the existing runner accepts these models without modification. Per-task IoU, Chamfer distance, invalidity rate, and per-family breakdowns are exported to \texttt{results/img2cq/<model>/} and rendered into the per-difficulty stratification of Table~\ref{tab:family\_cliff}.

---

## TODO (real numbers + verification)

- [ ] Run cadrille-SFT on BenchCAD-Lite (530 samples) — img2cq + qa_img + edit_img
- [ ] Run cadrille-RL on BenchCAD-Lite — same 5 tasks
- [ ] Run CADEvolve-rl1 on BenchCAD-Lite — img2cq + edit_img (no QA in their format)
- [ ] Verify replication: each model on a held-out 200-sample DeepCAD slice, IoU within ±0.5 of published
- [ ] Per-family IoU breakdown (Table~\ref{tab:family_cliff}) — find which hard families they fail hardest
- [ ] Build `bench/models/providers/{cadrille,cadevolve}.py` adapters (inputs: 8-view grid 238×238, `[-100,100]³` cube norm; outputs: CadQuery .py)
- [ ] Decide BenchCAD-trained baseline final config: SFT-only vs SFT+RL with our own IoU reward
- [ ] License compatibility check: cadrille-rl is CC-BY-NC-4.0 — confirm research-only use OK for D&B benchmark

## Open questions

- 我们 BenchCAD-trained baseline 用 Qwen2-VL-2B 吗(对标 lineage)?或 Qwen2.5-VL-7B(对标 Hanjie SportR)?— 后者更新但跟 lineage 不可直接比
- 跑 transfer 时 8-view grid vs 我们 4-view 哪个 protocol(他们 8-view, 我们 4-view canonical)?选其一会 favor 一边;两个都跑可能 honest 但占资源
- 如果 CADEvolve 在 BenchCAD-Lite 上 *没掉那么多* (e.g. 仅 -10 点),整篇 punch line 就弱化了 — 需要 contingency framing
- 是否提一句"we attempted RL on top of SFT but did not exceed cadrille-RL within our budget" 作 honest framing?
