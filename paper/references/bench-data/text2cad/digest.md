# text2cad — Text2CAD: Generating Sequential CAD Models from Beginner-to-Expert Level Text Prompts

**Venue:** NeurIPS D&B Spotlight · **Year:** 2024 · **URL:** https://arxiv.org/abs/2409.17106 · **PDF:** raw.pdf

## TL;DR
Khan et al. release the first text→parametric-CAD dataset by VLM+LLM annotating DeepCAD's 170K models with ~660K natural-language prompts at four skill levels (L0 abstract → L3 expert) and train a BERT+autoregressive Transformer that crushes a DeepCAD baseline on geometry (Median CD 0.37 vs 32.82, IR 0.93% vs 10.0%).

## Storyline (5-piece)
- **Problem.** Modern CAD has no AI-assisted text→CAD: existing text→3D outputs mesh/NeRF (not editable), VLMs misread CAD shapes (e.g. hollow cylinder as toilet paper), and no public dataset pairs natural language with parametric construction sequences.
- **Contribution.** (1) Two-stage annotation pipeline (LLaVA-NeXT shape descriptions → Mistral-50B multi-level prompt expansion) yielding ~660K text annotations across four skill levels for ~170K DeepCAD models; (2) Text2CAD Transformer with BERT encoder + 8-layer autoregressive decoder + Adaptive Layer; (3) GPT-4V-based + 5-designer user-study evaluation protocol.
- **Evidence (approach).** Construction sequence quantized to 8-bit tokens (256-class), Nc=272; text Np=512. Adaptive Layer fuses text features at each decoder block — drives Invalid Ratio down 2.9×.
- **Experiments.** Single trained baseline = DeepCAD reformulated for text input. Metrics: F1 (line/arc/circle/extrusion), Median/Mean Chamfer Distance (unit-bbox normalized), Invalidity Ratio (IR). Headline (L3 expert prompts): F1 line 81.13 vs 76.78; F1 arc 36.03 vs 20.04 (+80%); F1 circle 74.25 vs 65.14; F1 extrusion 93.31 vs 88.72; Median CD 0.37 vs 32.82 (88.7×); Mean CD 26.41 vs 97.93; IR 0.93% vs 10.00%. GPT-4V two-alternative eval (1000/level): Text2CAD wins L2/L3 (58.8/63.24 vs 40.2/36.06), close on L0/L1.
- **Analysis.** LLaVA is sensitive to perspective; DeepCAD is rect/cyl-imbalanced; no standardized eval benchmark exists; arc/loop-heavy parts and abstract prompts (L0) are still hardest. Adaptive Layer ablation: removing it drops arc F1 by 32.56% and triples IR.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | Designer text prompts → parametric CAD assembly with abstract vs detailed prompt examples. | Sells the multi-level skill-aware framing. |
| 2 | 4 | figure | pipeline | Two-stage VLM (shape) + LLM (multi-level prompt) annotation pipeline applied to DeepCAD JSON. | Defines how 660K prompts are produced. |
| 3 | 8 | table | headline-results | Main quantitative table: F1 / Mean+Median CD / IR across L0–L3 vs DeepCAD baseline + AL ablation. | Establishes geometry & validity wins. |
| 4 | 9 | figure | case-study | Qualitative reconstructions across L0–L3 prompts (Text2CAD vs DeepCAD vs GT). | Shows abstract prompts still produce coherent geometry. |

CHECKED: figs/fig01_hero.png, figs/fig04_pipeline.png, figs/fig08_headline-results.png, figs/fig09_case-study.png all exist.

## Takeaways for BenchCAD
- **Borrow the 4-level prompt framing (L0–L3)** as a difficulty axis; map our easy/medium/hard to a documented param/op-count basis to be defensible against this benchmark.
- **Steal the dual eval protocol** (GPT-4V 2-alternative verdict at fixed N=1000/level + 5-designer user study) — strong template for our multi-task reports.
- **Differentiate on data provenance**: Text2CAD inherits DeepCAD's rect/cyl bias and 8-bit token output is non-executable; BenchCAD's 106 family registry produces executable CadQuery directly with verified IoU≥0.99.
- **Avoid their Achilles heel** — token validity ≠ geometric correctness. Our IoU-via-build verification answers a critique reviewers will make of any token-IR-only paper.
- **Cite as the first-mover** for text→parametric CAD; position BenchCAD as multi-task multimodal + verifiable rather than text-only generation.

## One-line citation
`Khan, Sinha, Sheikh, Ali, Afzal, Stricker (2024). Text2CAD: Generating Sequential CAD Models from Beginner-to-Expert Level Text Prompts. NeurIPS D&B Spotlight.`
