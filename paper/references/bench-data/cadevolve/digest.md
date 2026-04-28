# cadevolve — CADEvolve: Creating Realistic CAD via Program Evolution

**Venue:** arXiv preprint · **Year:** 2026 · **URL:** https://arxiv.org/abs/2602.16317 · **PDF:** raw.pdf

## TL;DR
Elistratov et al. evolve 7,945 multi-operation parametric CadQuery generators from 46 hand-written seeds via VLM-guided propose-execute-filter loops, expanding to a unified ~1.3M-script training corpus (CADEvolve-3L) that breaks the sketch-extrude monoculture and lifts cadrille's Image2CAD SOTA further on DeepCAD/Fusion360/MCB.

## Storyline (5-piece)
- **Problem.** Open CAD program corpora (DeepCAD, Fusion360 Gallery, CAD-Recode) are 99% sketch-extrude. Richer ops (revolve / loft / sweep / fillet / chamfer / shell / patterns) are absent from released histories. Frozen-VLM single-pass synthesis (3D-Premise, CADCodeVerify, Seek-CAD) still produces simple parts.
- **Contribution.** (1) **Pipeline**: offline propose-execute-filter evolutionary loop with GPT-5-mini as proposer + 4-stage validation (execute / geometry validity / single-solid / vis-text agreement); (2) **3-tier dataset**: G (7,945 parametric generators), P (~8×10⁵ executable scripts with paired geometry), C (~1×10⁶ canonicalized scripts after filtering, ~2.7M after rotation+rewrite augmentation); (3) **CADEvolve-M policy**: Qwen2-VL-2B fine-tuned on CADEvolve-C, SOTA Image2CAD across DeepCAD, Fusion360, MCB.
- **Evidence (approach).** Shape-tuple representation P = {name, abstract, detailed, code:param2cq, parents}. Seed pool covers extrude/revolve/loft/sweep/shell/fillet/chamfer/booleans/patterns. Code-style augmentation via gpt-5-mini producing ≤10 semantically-equivalent rewrites per script (744,780 valid). Rotation augmentation adds 1,337,553 → 2,720,481 SFT scripts.
- **Experiments.** Image2CAD via 8-view canonical grid (6 ortho ±X/±Y/±Z + 2 iso) into Qwen2-VL-2B. Median CD ↓ ×10³ / Mean IoU% ↑ / IR% ↓. Headline (CADEvolve-C big RL2): DeepCAD **0.16/91.1/0.1**; Fusion360 **0.16/84.0/0.2**; MCB **0.52/55.2/0.4**. Beats cadrille RL on DeepCAD/Fusion360 image; first to report MCB (cadrille didn't test). Reward = 10·IoU if compiles else -10 (same as cadrille). RL1 vs RL2: RL2 adds MCB train split for distribution match.
- **Analysis.** SFT on naive-traced scripts caused template overfitting (Qwen2-VL-2B copied skeletons) — code-style rewrites + canonicalization were essential. Even after augmentation, sketch+extrude-only baselines fail on revolve/sweep/loft/fillet targets which CADEvolve handles well.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | Pipeline overview: shape tuple representation + seed pool + propose-retrieve-validate-select loop. | Six-panel pipeline schematic. |
| 2 | 5 | figure | data-stats | Gallery of accepted CADEvolve-G outputs covering extrude/revolve/loft/sweep/shell/fillet/chamfer/booleans/patterns. | Visual op coverage proof. |
| 3 | 8 | table | headline-results | Table 1: Image2CAD on DeepCAD/Fusion360/MCB across cadrille SFT/RL, CADEvolve-P/C variants, RL1/RL2. | Establishes new SOTA. |
| 4 | 9 | figure | case-study | Qualitative DeepCAD/Fusion360/MCB rows: cadrille baseline vs CADEvolve-M vs target. | Shows cadrille fails on revolve/sweep parts CADEvolve handles. |

CHECKED: figs/fig01_hero.png, figs/fig05_data-stats.png, figs/fig08_headline-results.png, figs/fig09_case-study.png all exist.

## Takeaways for BenchCAD
- **Validates BenchCAD's core thesis** that op-diversity matters: CADEvolve explicitly cites the sketch-extrude monoculture problem. We should cite them and contrast: 7,945 generators (LLM-evolved) vs our 106 hand-curated families (registry-driven, parametric ranges hand-tuned).
- **Borrow the 4-stage validation**: execution → geometry validity → single-solid → vis-text agreement. Our pre-flight rule already does (1)-(3); add (4) as a future improvement.
- **Their 8-view (6 ortho + 2 iso) grid** is a stronger image-conditioning protocol than cadrille's 4-iso. We should match this rendering convention to enable 1:1 comparison.
- **Differentiate on benchmark vs corpus**: CADEvolve-3L is a 1.3M-script training corpus; BenchCAD is an evaluation suite with 5 tasks. Frame as orthogonal — train on CADEvolve, evaluate on BenchCAD.
- **Same-lab follow-up to cadrille**: must cite as a pair. CADEvolve = cadrille pipeline + much larger evolved synthetic data. Both use Qwen2-VL-2B + Dr.CPPO.

## One-line citation
`Elistratov, Barannikov, Konushin, Ivanov, Kuznetsov, Khrulkov, Zhemchuzhnikov (2026). CADEvolve: Creating Realistic CAD via Program Evolution. arXiv 2602.16317.`
