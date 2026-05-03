# cap3d — Scalable 3D Captioning with Pretrained Models (Cap3D)

**Venue:** NeurIPS 2023 D&B · **Year:** 2023 · **URL:** https://cap3d-um.github.io/ · **PDF:** raw.pdf

## TL;DR
Automatic 3D-captioning pipeline (BLIP2 → CLIP-filter → GPT-4 fuse over 8 views) produces 785k caption-3D pairs on Objaverse that beat crowdsourced captions in human A/B testing while costing 10× less and running 40× faster.

## Storyline (5-piece)
- **Problem.** 3D-text data is scarce; Objaverse metadata is short/empty; manual annotation of 800k assets is intractable.
- **Contribution.** Cap3D: side-step humans by chaining pretrained image captioner, image-text aligner, and LLM summarizer; release 785k Objaverse + 17k ABO geometry captions plus 41k human captions for evaluation.
- **Evidence (approach).** Render M=8 Blender views @ 512², BLIP2 generates N=5 captions/view, CLIP picks best-matching caption per view, GPT-4 fuses 8 captions into one paragraph; ABO uses two-stage QA prompting for geometry detail.
- **Experiments.** 36k human A/B votes over 22k objects: Cap3D wins 52.3% vs human 37.8% (9.5% tie). Cost $8.35/1k vs $87.18/1k human; throughput 65k/day vs 1.4k/day. Finetune Point·E, Shap·E, DreamFields, DreamFusion on Cap3D — improves text-to-3D quality.
- **Analysis.** Ablations show every stage matters (BLIP2-only → CLIP filter → +GPT-4); Cap3D captions outperform human captions even at matched scale; on geometric ABO captions Cap3D underperforms humans on captioning but beats humans when reformulated as QA.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 1 | 1 | caption gallery + table | hero | 12 example 3D-caption pairs + cost/quality table vs human | Caption richness and headline win-rate over humans |
| 4 | 4 | pipeline diagram | pipeline | M=8 renders → BLIP2×5 → CLIP filter → GPT-4 fuse | Architecture of the auto-captioning chain |
| 5 | 5 | dataset compare | data-stats | Objaverse human vs metadata vs Cap3D length histogram | Cap3D is longer and more descriptive than alternatives |
| 8 | 8 | text-to-3D grid | human-vs-model | Generated 3D from Point·E etc. before/after Cap3D finetune | Cap3D-finetuned generators produce better 3D |
| 9 | 9 | results table | headline-results | Quantitative text-to-3D metrics for SOTA finetuned on Cap3D | Captions translate into measurable downstream gain |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: model-chain annotation (renderer → captioner → CLIP filter → LLM fuse) is the right template for auto-labeling CAD parts with descriptions / intents.
- Borrow: human A/B evaluation on a small subset (~40k captions) is sufficient to validate auto-labels — don't need full-corpus human eval.
- Borrow: cost/speed/quality table (Cap3D Table 1 style) is a single high-impact figure for a D&B submission.
- Contrast: Cap3D targets free-form descriptions; BenchCAD needs structured parametric labels (constraints, dims) — pure VLM captioning won't suffice.
- Avoid: relying solely on forward-facing renders — Cap3D explicitly motivates 8 views for self-occlusion; CAD bench should similarly use multi-view + section views.

## One-line citation
Luo et al., "Scalable 3D Captioning with Pretrained Models," NeurIPS 2023 D&B.
