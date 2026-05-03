# cadrille — cadrille: Multimodal CAD Reconstruction with Reinforcement Learning

**Venue:** ICLR · **Year:** 2026 · **URL:** https://arxiv.org/abs/2505.22914 · **PDF:** raw.pdf

## TL;DR
Kolodiazhnyi et al. unify point-cloud + multi-view image + text CAD reconstruction in one Qwen2-VL-2B backbone, two-stage SFT (1M procedural CadQuery + DeepCAD 160K) + online RL with Dr. CPPO and IoU reward, setting new SOTA on 10 benchmarks across 4 datasets including real-world CC3D.

## Storyline (5-piece)
- **Problem.** Existing CAD reconstruction is single-modality (point clouds dominate); the few multimodal attempts are far worse than single-modal SOTA. Procedural-data models don't transfer to real-world; handcrafted CAD datasets are tiny.
- **Contribution.** (1) First multimodal VLM (Qwen2-VL-2B) accepting all of point/image/text in one model, outputting executable CadQuery; (2) 3-stage pipeline: pretrain (reused) → SFT on procedural+DeepCAD → RL on mesh-only data (no CAD seq labels needed); (3) reward R = 10·IoU + (-10 if invalid), uses Dr. CPPO (Dr. GRPO + CPPO) — strong-signal sample selection, no ref model.
- **Evidence (approach).** Single linear projection for point clouds (à la CAD-Recode), VLM visual encoder for images, tokenizer for text. Hard-example mining: only train on SFT-mean-reward<7.5 cases. Sampling T=1.0, K=5 (DPO).
- **Experiments.** Median CD ×10³ / Mean IoU% / IR%. Headline: **DeepCAD-pt** SFT 0.18/87.1/2.1 → RL **0.17/90.2/0.0** (vs CAD-Recode 0.18/87.1/3.1); **DeepCAD-img** RL **0.17/92.2/0.0** (vs CADCrafter 0.26/-/3.6); **Fusion360-img** RL **0.17/84.6/0.0**; **CC3D-pt real** RL **0.47/67.9/0.2**; **CC3D-img** RL **0.57/65.0/0.1**. RL drives IR to ~0 across the board. Cross-modal RL transfer: image RL also lifts point-cloud scores.
- **Analysis.** SFT alone with R+D mix degrades vs R-only; RL is the bridge between procedural and real-world domains. SFT inherits CAD-Recode sketch+extrude bias — RL can fix invalid rate but can't add operator vocabulary the SFT model never saw.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 2 | figure | gap-vs-prior | cadrille vs CAD-Recode: 2-stage→3-stage training, single-modal→multimodal. | Two-axis novelty diagram. |
| 2 | 4 | figure | pipeline | Multimodal data generation: point/image/text inputs unified, RL with mesh-only handcrafted set. | Shows RL needs no CAD seq labels. |
| 3 | 8 | table | headline-results | DeepCAD test set table: cadrille SFT/RL vs all single-modal baselines (CAD-Recode, CAD-SIGNet, etc.). | Establishes SOTA across point/image/text. |
| 4 | 9 | figure | case-study | Reconstruction examples on DeepCAD/Fusion360/CC3D from point cloud + image + text. | Multimodal qualitative coverage. |

CHECKED: figs/fig02_gap-vs-prior.png, figs/fig04_pipeline.png, figs/fig08_headline-results.png, figs/fig09_case-study.png all exist.

## Takeaways for BenchCAD
- **Use cadrille-rl as a primary baseline** — public HF model (maksimko123/cadrille-rl), inference-only, no API. Run on our img2cq held-out and report Median CD/IoU/IR with their convention.
- **Borrow the reward** R = 10·IoU + (-10 if invalid) but adapt to our rotation-invariant IoU. Also borrow the Dr.CPPO hard-example mining trick (only train cases where mean reward < threshold).
- **Differentiate**: their data backbone is CAD-Recode (sketch+extrude only) + DeepCAD; under our 106 family op-diverse data they will fail on revolve/loft/sweep/fillet families — quantify this gap as our headline finding.
- **CC3D real-world is their robustness brand**; we should NOT directly compete on CC3D — instead position BenchCAD as op-diversity stress test orthogonal to real-scan robustness.
- **Same-lab follow-up**: cadrille and CADEvolve share authors (Rukhovich, Zhemchuzhnikov, Konushin); cite both together as "Russian-lab Qwen2-VL-2B + Dr.GRPO line".

## One-line citation
`Kolodiazhnyi, Tarasov, Zhemchuzhnikov, Nikulin, Zisman, Vorontsova, Konushin, Kurenkov, Rukhovich (2026). cadrille: Multimodal CAD Reconstruction with Reinforcement Learning. ICLR.`
