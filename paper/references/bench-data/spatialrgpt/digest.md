# spatialrgpt — SpatialRGPT: Grounded Spatial Reasoning in Vision-Language Models

**Venue:** NeurIPS 2024 · **Year:** 2024 · **URL:** https://www.anjiecheng.me/SpatialRGPT · **PDF:** raw.pdf

## TL;DR
Region-aware VLM trained on an auto-curated 3D-scene-graph dataset (Open Spatial Dataset: 1M images, 8.7M spatial concepts, 5M regions) with a "depth plugin" connector, plus SpatialRGBT-Bench — a ground-truth 3D benchmark covering relative + metric spatial QA across indoor/outdoor/sim.

## Storyline (5-piece)
- **Problem.** VLMs fail at left/right, near/far, behind/front; existing region VLMs use bbox text that confounds the LLM, and prior work (SpatialVLM) lacks region targeting and exact metric grounding.
- **Contribution.** (i) 3D scene-graph auto-curation pipeline from single RGB; (ii) Open Spatial Dataset (OSD) with 8M template + 700k LLM QA; (iii) SpatialRGPT model = region-feature extractor + depth plugin connector on LLaMA2-7B; (iv) SpatialRGBT-Bench with GT 3D annotations.
- **Evidence (approach).** Pipeline: open-vocab tag → GroundingDINO box → SAM mask → Metric3Dv2 metric depth → WildCamera intrinsics → PerspectiveFields canonicalization → 3D bbox graph with 6 relative + 4 metric edge types. Train via 3-stage NVILA-style recipe; depth-connector trained only on spatial QAs to keep RGB-only path intact.
- **Experiments.** SpatialRGBT-Bench split into qualitative (Below/Above, Left/Right, Big/Small, Tall/Short, Wide/Thin, Behind/Front) + quantitative (direct/horizontal/vertical distance, width/height/direction); compare GPT-4V, Gemini, LLaVA, RegionGPT. SpatialRGPT large gains, esp. on metric questions; downstream: region-aware reward annotator for robotics, multi-hop reasoning.
- **Analysis.** Depth plugin essential for metric; template QA gives basic grounding, LLM QA gives reasoning, blend gives best generalization. Standard VL benches don't regress.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 1 | 1 | example dialog grid | hero | Region-tagged QA: relative, metric, multi-hop reasoning examples | Capability palette and region-prompt UX |
| 4 | 4 | curation pipeline | pipeline | Image→tag/det/seg→depth+intrinsics+canonicalization→3D graph | Auto-data construction chain |
| 5 | 5 | template + LLM QA | taxonomy | Two-row sample QAs: template basics + LLM reasoning | Two complementary supervision flavors |
| 6 | 6 | model architecture | pipeline | RGB+depth dual encoders, region extractor, LLaMA2 with depth plugin | Where depth modality enters the VLM |
| 7 | 7 | results table | headline-results | Per-relation accuracy vs GPT-4 / Gemini / RegionGPT | Quantitative gap closed by region+depth |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: split benchmark into qualitative (categorical) + quantitative (metric) — directly maps to "is this an extrude?" vs "what is the extrude depth in mm?" for CAD code-gen.
- Borrow: depth/auxiliary-modality plugin connector that trains only on bench-specific data — useful framing for CAD where 3D STEP/B-rep is auxiliary modality.
- Borrow: GT 3D annotations are explicit selling point — BenchCAD must emphasize ground-truth parametric programs vs prior visual-only datasets.
- Contrast: SpatialRGPT generates QAs from auto scene-graphs (noisy); CAD has clean parametric GT, so we should not stop at QA — we should grade executable code.
- Avoid: reporting only relation-classification accuracy; reviewers expect mean-error metrics on metric quantities (distance, height) — analog for CAD is mm-error on extrusion height, IoU on sketch.

## One-line citation
Cheng et al., "SpatialRGPT: Grounded Spatial Reasoning in Vision-Language Models," NeurIPS 2024.
