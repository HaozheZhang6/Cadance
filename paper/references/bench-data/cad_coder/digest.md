# cad_coder — CAD-Coder: Text-to-CAD Generation with Chain-of-Thought and Geometric Reward

**Venue:** NeurIPS 2025 (preprint, also IDETC 2025 line) · **Year:** 2025 · **URL:** https://arxiv.org/abs/2505.19713 · **PDF:** raw.pdf

## TL;DR
Guan et al. reformulate text→CAD as text→CadQuery code, train Qwen2.5-7B with SFT + GRPO using a Chamfer-Distance reward + CoT cold-start, and on the Text2CAD test set push Mean CD to 6.54 ×10⁻³ (4.5× over Text2CAD) using a 110K LLM-back-synthesized triplet dataset.

## Storyline (5-piece)
- **Problem.** Command-sequence text→CAD (DeepCAD/Text2CAD) cannot be directly executed for verification, has narrow op vocabulary (sketch+extrude only), and produces tokens that are hard to interpret/edit.
- **Contribution.** (1) Reformulate text→CAD as text→CadQuery (executable Python DSL); (2) Two-stage SFT + GRPO RL with CAD-specific reward = piecewise CD reward + format reward; (3) 1.5K human-refined CoT cold-start; (4) 110K text–CadQuery–3D triplet dataset filtered by CD with three quality bins (8K CD<1e-4 / 70K CD<1e-3 / 32K hard).
- **Evidence (approach).** GRPO with k=8 candidates/prompt, β=0.001 KL; CD reward = 1.0 if CD<1e-5, 0 if CD>0.5 or exec-fail, linear interpolation in between. SFT on the 8K high-quality split first, then RL. CoT template breaks generation into 6 reasoning steps (analyze → primitive choice → sketch plan → param select → operation choice → code).
- **Experiments.** Mean/Median CD (×10³) + IR. Trained baselines: Text2CAD. Zero-shot LLM baselines: Claude-3.7-Sonnet / GPT-4o / DeepSeek-V3 / Qwen2.5-72B / Qwen2.5-7B. Headline (Text2CAD test): CAD-Coder Mean CD **6.54** / Median 0.17 / IR **1.45%** vs Text2CAD 29.29 / 0.37 / 3.75 vs GPT-4o 133.52/45.91/93. Ablation: SFT-only Mean CD 74.55, w/o CoT 17.34, full 6.54. Quality > quantity: 8K curated → 6.54 vs 70K medium → 9.89.
- **Analysis.** RL helps multimodal coverage but reward-hacks on thin walls and overlapping features; multi-component spatial alignment still fails. Editing is "promising" but unmeasured.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | Title page + abstract framing reformulation of text→CAD as text→CadQuery code with CoT and geometric RL. | Establishes thesis and contribution list. |
| 2 | 4 | figure | pipeline | CAD-Coder training pipeline: SFT cold-start → GRPO RL with CD + format reward, CoT prompts. | Architecture and reward decomposition. |
| 3 | 7 | figure | case-study | Qualitative comparison: target vs Text2CAD vs zero-shot GPT-4o/DeepSeek-V3/Qwen vs CAD-Coder. | Visual gap on multi-component parts. |
| 4 | 8 | table | headline-results | Main quantitative table: Mean/Median CD ×10³ + IR across all baselines on Text2CAD test set. | Establishes 4.5× CD margin over Text2CAD. |

CHECKED: figs/fig01_hero.png, figs/fig04_pipeline.png, figs/fig07_case-study.png, figs/fig08_headline-results.png all exist.

## Takeaways for BenchCAD
- **Borrow the piecewise CD reward design** (CD<ε → 1, CD>τ → 0, linear in between) as a template for our edit pass-rate reward / scoring.
- **Cite the "quality > quantity" 8K vs 70K finding** as direct support for our small-but-curated 20K verified set vs their 110K LLM-resynthesized.
- **Differentiate**: their 110K is Deepseek-V3 back-translation from Text2CAD/DeepCAD (sketch+extrude bias inherited); our 106-family registry produces fillet/loft/sweep/revolve/boolean coverage with builder-verified IoU≥0.99.
- **Match their zero-shot LLM baseline lineup** (Claude-3.7-Sonnet, GPT-4o, DeepSeek-V3, Qwen2.5-72B/7B) — this is the NeurIPS 2025 standard for text→CAD; reviewers will demand it.
- **Avoid their gap**: they only evaluate single text→CAD task with CD/IR; we add img2cq + qa + edit. Their failure modes (overlapping features reward-hacking, multi-component alignment) are exactly what BenchCAD's family-aware difficulty stratification can probe.

## One-line citation
`Guan, Wang, Xing, Zhang, Xu, Yu (2025). CAD-Coder: Text-to-CAD Generation with Chain-of-Thought and Geometric Reward. NeurIPS 2025.`
