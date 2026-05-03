# mllm_compbench — MLLM-CompBench: A Comparative Reasoning Benchmark for Multimodal LLMs

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://compbench.github.io · **PDF:** raw.pdf

## TL;DR
~40K image-pair triplets across 8 relativity dimensions (attribute/existence/state/emotion/temporal/spatial/quantity/quality) reveal MLLMs (GPT-4V/Gemini/LLaVA-1.6) struggle especially on existence, spatial, quantity comparisons.

## Storyline (5-piece)
- **Problem.** MLLM benches use a single image; humans constantly compare two scenes (which is fresher? closer? earlier?). Comparative reasoning is core to AGI but unmeasured.
- **Contribution.** MLLM-CompBench: 39.8K (image_left, image_right, question, answer) triplets sampled across 14 visual domains (animals, fashion, sports, indoor, outdoor, …). Eight relativity types defined and balanced. Pairs mined via metadata + CLIP-similarity, then human-verified.
- **Evidence (approach).** For each relativity type, source from existing labeled datasets (CUB for birds, AVA aesthetics, etc.) using metadata to derive ground-truth comparisons; CLIP filters near-duplicates; human annotators sanity-check pair + question + answer.
- **Experiments.** Benchmark GPT-4V, Gemini-Pro, LLaVA-1.6, VILA-1.5; horizontal-concat both images for input. Two-stage prompting (per-image description → text-only compare) tested as oracle/upper bound.
- **Analysis.** Closed models clearly lead but all <80% even on attribute; existence/spatial/quantity worst (~50–60%). Two-stage helps but doesn't close the gap → bottleneck is joint visual reasoning, not language.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 1 | gallery | taxonomy | 16 image-pair examples covering all 8 relativity types. | Visual taxonomy + GPT-4V predictions per type. |
| 2 | 4 | source table | data-stats | Source datasets per relativity, pair counts, domains. | 14-domain coverage; how pairs are mined. |
| 3 | 7 | flow diagram | pipeline | Pair-mining: metadata filter → CLIP filter → human verify. | End-to-end curation reproducible. |
| 4 | 8 | results table | headline-results | Accuracy per model × relativity type. | GPT-4V leads but spatial/quantity ~50%. |
| 5 | 9 | qualitative | failure-cases | Error examples per failing relativity (existence/spatial). | Highlights joint-visual-reasoning gap vs language. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow comparative-reasoning task class: in CAD show two parts and ask "which has smaller wall thickness / which has more holes / which is symmetric" — this isolates parametric perception from generation.
- Borrow 8-axis taxonomy structure: define 8 CAD-comparison axes (size/topology/symmetry/feature-count/material-removal/tolerance/manufacturability/pattern) — produces a clean radar plot.
- Borrow 2-stage prompting ablation: per-image describe then compare → measures whether failure is in vision or fusion. Strong diagnostic for our paper.
- Borrow source-mining strategy: re-use already-labeled CAD datasets (Fusion360, ABC, DeepCAD) to derive automatic comparisons via metadata diff.
- Avoid: our generation task is single-input; comparative is a complementary mini-task, not the main bench.

## One-line citation
Kil et al., "MLLM-CompBench: A Comparative Reasoning Benchmark for Multimodal LLMs," NeurIPS 2024 Datasets & Benchmarks.
