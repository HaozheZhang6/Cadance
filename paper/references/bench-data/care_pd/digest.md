# care_pd — CARE-PD: A Multi-Site Anonymized Clinical Dataset for Parkinson's Disease Gait Assessment

**Venue:** NeurIPS 2025 D&B · **Year:** 2025 · **URL:** https://neurips2025.care-pd.ca · **PDF:** raw.pdf

## TL;DR
Largest publicly released archive (8,477 walks, 18.66h, 9 cohorts, 8 clinical centers) of anonymized SMPL-mesh PD gait data with UPDRS scores; pretraining motion encoders on CARE-PD cuts MPJPE 60.8 → 7.5 mm and lifts macro-F1 by 17 pts on severity prediction.

## Storyline (5-piece)
- **Problem.** PD gait research is stuck on small single-site datasets that don't generalize across sites; no public clinically-labeled large 3D motion corpus exists.
- **Contribution.** CARE-PD: harmonized 9-cohort dataset (RGB + MoCap → SMPL meshes @30 Hz), four generalization protocols (within-dataset / cross-dataset / LODO / MIDA), and benchmarks for two tasks: UPDRS-gait severity classification + motion pretext (2D→3D lifting, 3D recon).
- **Evidence (approach).** MoCap pipeline: marker→22 SMPL joints→SparseFusion fit. RGB pipeline: WHAM monocular mesh recovery + Kabsch slope correction + clean-segment curation. Anonymization keeps only textureless mesh params. 7 SOTA encoders evaluated frozen + linear/kNN probe; engineered Random-Forest baseline (cadence, step length, stability, foot lifting, etc.).
- **Experiments.** Severity prediction macro-F1 (with/without rare class 3) under 4 protocols; 7 motion encoders (POTR, MixSTE, PoseFormerV2, MotionBERT, MotionAGformer, MotionCLIP, MoMask) vs handcrafted RF. Pretext: MotionAGFormer (lifting) + MoMask (recon) trained from scratch or finetuned on CARE-PD.
- **Analysis.** Encoders > handcrafted features; MoMask most robust transfer. Cross-site drops F1 by 0.2–0.4. CARE-PD pretraining drops MPJPE from 60.8 mm to 7.5 mm and adds +17 pts on severity macro-F1, proving clinical utility of pretraining on diverse pathological gait.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 3 | 3 | dataset table | data-stats | 9 sub-datasets: subjects, walks, modality, FPS, age, annotations | Composition and clinical labels per site |
| 4 | 4 | pipeline diagram | pipeline | SMPL extraction from MoCap/RGB, 4 evaluation protocols | End-to-end harmonization + benchmark setup |
| 7 | 7 | within/cross matrices | headline-results | Heatmap of within- and cross-dataset macro-F1 | Domain shift quantified; MoMask robustness |
| 8 | 8 | LODO/MIDA | ablation | LODO and MIDA results across encoders | Diversity dilutes site bias; in-domain finetune helps |
| 9 | 9 | scatter / curves | correlation | MPJPE drop and severity-F1 gain after CARE-PD pretrain | Pretraining gain quantified |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: four-protocol framework (within / cross / LODO / MIDA) is the gold-standard generalization story for any multi-source benchmark — directly applicable to BenchCAD's mix of Fusion360, DeepCAD, ABC, synthetic.
- Borrow: pretraining-utility experiment (encoder pretrained on bench → boost on downstream task) is the most persuasive D&B argument and reviewers expect it.
- Borrow: include both learned-representation and handcrafted-feature baselines to legitimize neural approaches.
- Contrast: CARE-PD's privacy story (textureless meshes only) doesn't apply, but the licensing + IRB framing is a template for any sensitive-data D&B submission.
- Avoid: reporting only single aggregate metric — F1 with/without rare class is the right move for imbalanced labels; CAD analog is split metric for rare op-types (loft, sweep).

## One-line citation
Adeli et al., "CARE-PD: A Multi-Site Anonymized Clinical Dataset for Parkinson's Disease Gait Assessment," NeurIPS 2025 D&B.
