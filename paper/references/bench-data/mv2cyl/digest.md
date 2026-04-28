# mv2cyl — MV2Cyl: Reconstructing 3D Extrusion Cylinders from Multi-View Images

**Venue:** NeurIPS 2024 · **Year:** 2024 · **URL:** https://mv2cyl.github.io · **PDF:** raw.pdf

## TL;DR
First method that reverse-engineers a Sketch-Extrude CAD program (axis, sketch, height) directly from multi-view RGB images by jointly distilling 2D surface and curve segmentations into paired neural fields, beating Point2Cyl(+NeuS2) on Fusion360 and DeepCAD by large margins.

## Storyline (5-piece)
- **Problem.** Reverse-engineering CAD extrusion cylinders has only been done from clean point clouds; 3D backbones are the bottleneck and 3D scans usually arrive with multi-view images anyway.
- **Contribution.** MV2Cyl: a multi-view-only pipeline combining (i) 2D surface segmentation (instance + start/end/barrel), (ii) 2D curve segmentation (instance + start/end), (iii) a paired surface field + curve field in 3D, (iv) closed-form parameter recovery for (n, c, h, S̃, s).
- **Evidence (approach).** Two U-Nets give per-pixel labels with Hungarian-matched losses (CE + dice + focal); TensoRF-backed density+semantic fields integrate views in 1500 iters; RANSAC plane fit gives axis, IGR fits implicit sketch, paired centers give height/centroid. Surfaces give axis/height; curves give the 2D sketch — they synergize, neither alone suffices.
- **Experiments.** Fusion360 + DeepCAD splits from Point2Cyl. Metrics: extrusion-axis error E.A., extrusion-center E.C., extrusion-height E.H., per-cyl fit and global fit. MV2Cyl reduces E.A. on Fusion360 from 9.52° (Point2Cyl) → 1.39°, E.H. 0.29 → 0.14, Fit-Cyl 0.07 → 0.028.
- **Analysis.** Ablating either curve or surface branch hurts; NeuS2+Point2Cyl baseline collapses (E.A. 35°), confirming naive reconstruct-then-fit fails due to albedo/shading ambiguity. Hungarian matching is required because instance labels are arbitrary.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 1 | 1 | hero overview | hero | Multi-view → 2D segs → 3D fields → CAD params + edit ops | End-to-end framing of MV-image → editable CAD |
| 3 | 3 | pipeline diagram | pipeline | Surface and curve U-Nets feeding 3D fields and reconstruction | Two-branch architecture and stage flow |
| 5 | 5 | seg examples | taxonomy | Predicted instance / start-end / barrel masks per view | What each branch outputs and label space |
| 8 | 8 | results table + qualitative | headline-results | Fusion360/DeepCAD numbers vs Point2Cyl baselines | Large margin on every metric |
| 9 | 9 | case study | case-study | Reconstructed CAD vs GT on diverse parts | Qualitative fidelity & failure modes |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: explicit per-extrusion ground-truth labels (axis, center, height, sketch, scale) — exactly the parameter schema BenchCAD should expose for code-gen scoring.
- Borrow: dual surface/curve evaluation reveals which sub-skill a model fails at; BenchCAD should likewise score sketch-recovery vs extrusion-param recovery separately.
- Contrast: MV2Cyl is method paper, only Fusion360+DeepCAD (~tens of thousands); BenchCAD's value-add is scale + diversity of CAD programs, not a new fitter.
- Avoid: sketch-only or surface-only metrics — must report both, mirroring MV2Cyl's E.A. / E.H. / Fit-Cyl split.
- Borrow: include a "naive reconstruct-then-fit" baseline (NeuS2→Point2Cyl style) to show why image→code direct mapping is non-trivial.

## One-line citation
Hong et al., "MV2Cyl: Reconstructing 3D Extrusion Cylinders from Multi-View Images," NeurIPS 2024.
