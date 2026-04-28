# objaverse_xl — Objaverse-XL: A Universe of 10M+ 3D Objects

**Venue:** NeurIPS 2023 D&B · **Year:** 2023 · **URL:** https://objaverse.allenai.org/objaverse-xl · **PDF:** raw.pdf

## TL;DR
Web-crawled 10.2M-object 3D dataset (13× larger than Objaverse 1.0, 200× larger than ShapeNet) that, when used to pretrain Zero123, yields strong zero-shot novel-view synthesis on in-the-wild images.

## Storyline (5-piece)
- **Problem.** 3D vision lags 2D/text because public 3D data is small and handcrafted (ShapeNet 51k, Objaverse 1.0 800k); scale, not architecture, is the bottleneck.
- **Contribution.** Objaverse-XL: 10.2M deduped 3D objects scraped from GitHub (37M files indexed), Thingiverse, Sketchfab, Polycam, Smithsonian, with Blender-render metadata and CLIP-derived NSFW/face/quality flags.
- **Evidence (approach).** Crawl + dedup by content hash (-23M dups), import-and-render in Blender (5.5M renderable), extract polygon/vertex/animation stats, NSFW + face + photogrammetry-hole classifiers via CLIP-MLP heads.
- **Experiments.** Pretrain Zero123-XL on novel-view synthesis using 100M+ multi-view renders; also retrain PixelNeRF. Evaluate zero-shot on Google Scanned Objects (PSNR/SSIM/LPIPS/FID) and qualitatively on cartoons, anime, sketches, furniture.
- **Analysis.** Scaling curves keep improving from 1k→10M assets with no plateau; alignment-finetune on high-quality subset further boosts PSNR 18.23→19.88, LPIPS 0.088→0.075. NSFW objects only 815/10M.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 1 | 1 | render grid | hero | Dense scene of objects across categories from Objaverse-XL | Diversity & visual scale of the corpus |
| 3 | 3 | t-SNE + table | data-stats | CLIP t-SNE of XL vs 1.0; counts vs other 3D datasets | XL densely covers shape distribution; 200× ShapeNet |
| 5 | 5 | source grid | taxonomy | Examples per source: GitHub, Thingi, Polycam, Smithsonian, Sketchfab | Source heterogeneity, Thingiverse color-randomized |
| 7 | 7 | comparison grid | headline-results | Zero123-XL vs Zero123 NVS on people, anime, cartoons, sketches | Pretraining scale unlocks zero-shot OOD generalization |
| 8 | 8 | scaling curves | ablation | PSNR/LPIPS vs # pretrain assets (1k→10M) for Zero123 + PixelNeRF | Monotone scaling, no saturation at 10M |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: dedup-by-content-hash + render-and-classify cleanup pipeline — directly applicable to filtering scraped CAD/STEP/STL.
- Borrow: scaling-law plot (asset-count x-axis, OOD metric y-axis) is the most persuasive single figure for a D&B paper.
- Contrast: Objaverse-XL leaves CAD parametric history un-recovered — BenchCAD's value-add is exactly the procedural ground-truth Objaverse lacks.
- Avoid: don't oversell raw mesh count; report "renderable", "deduped", "license-clean" subsets separately to preempt reviewer pushback.
- Borrow: NSFW/face/quality flags via CLIP-MLP are cheap and reviewer-expected for any web-scraped release.

## One-line citation
Deitke et al., "Objaverse-XL: A Universe of 10M+ 3D Objects," NeurIPS 2023 D&B.
