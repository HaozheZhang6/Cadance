# visual_cot — Visual CoT: Advancing Multi-Modal Language Models with a Comprehensive Dataset and Benchmark for Chain-of-Thought Reasoning

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://github.com/deepcs233/Visual-CoT · **PDF:** raw.pdf

## TL;DR
438K VQA pairs annotated with bounding-box "key-region" CoT supervision (98K with detailed step-by-step rationales) plus a multi-turn dynamic-zoom MLLM pipeline; trained models substantially outperform vanilla LLaVA on a new region-grounded benchmark.

## Storyline (5-piece)
- **Problem.** MLLMs are black boxes lacking interpretability; on high-resolution images with small key regions they fail because they process everything at fixed resolution; existing VQA datasets have no intermediate region supervision.
- **Contribution.** (1) 438K visual-CoT dataset with bounding-box annotations indicating the answer-relevant image region across 5 domains (Text/Doc, General VQA, Fine-Grained, Charts, Relation Reasoning); ~98K items add full reasoning-step text. (2) Multi-turn pipeline that first predicts a bbox, crops, re-feeds, then answers — mimics human "look-and-zoom". (3) New evaluation benchmark for region-grounded VQA.
- **Evidence (approach).** Re-purpose existing VQA datasets (TextVQA, DocVQA, InfographicsVQA, GQA, OpenImages, Birds-200, etc.); use heuristics + GPT-4 generation for bbox + reasoning; quality-filter with human spot-check.
- **Experiments.** Train LLaVA-1.5/Vicuna with the new annotations + pipeline; evaluate on visual-CoT bench across 5 domains. Significant gains over vanilla LLaVA, especially on fine-grained and chart/text domains; ablations show bbox CoT > no CoT, and bbox CoT + reasoning steps > bbox alone.
- **Analysis.** Resolution ablation shows huge gains on high-res inputs; failure inspection shows residual errors mostly in bbox localization (not language reasoning) — motivating better visual grounding.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 4 | gallery | examples | Six sample items across 5 domains with red bbox + QA. | Defines the "key-region CoT" annotation. |
| 2 | 5 | source table | data-stats | Source datasets, sizes, GPT-4 use, descriptions for the 5 domains. | Shows the 438K composition. |
| 3 | 6 | flow diagram | pipeline | Multi-turn pipeline: image → bbox → crop → re-feed → answer. | Architecture for dynamic visual focus. |
| 4 | 7 | results table | headline-results | Vanilla vs Visual-CoT-trained model accuracy across 5 domains. | Significant gains from bbox supervision. |
| 5 | 8 | ablation table | ablation | bbox-only vs bbox+reasoning vs no-CoT comparisons. | Both bbox and steps contribute additive gains. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow intermediate-supervision idea: annotate every CAD part with primitive-level decomposition (extrude regions, holes, fillets) — analogous "key-region" supervision lets us train + evaluate stepwise generation.
- Borrow dynamic-zoom pipeline analogue: have model first locate key features (holes/fillets) in the input image, then generate per-feature CadQuery snippets — interpretable + better.
- Borrow per-domain breakdown table style; clean and informative.
- Borrow ablation: with/without CoT supervision; gains attributable to intermediate signal.
- Avoid: we should not use GPT-4-generated rationales as silver labels for the test set (contamination + noise) — only for train aug.

## One-line citation
Shao et al., "Visual CoT: Advancing Multi-Modal Language Models with a Comprehensive Dataset and Benchmark for CoT Reasoning," NeurIPS 2024 Datasets & Benchmarks.
