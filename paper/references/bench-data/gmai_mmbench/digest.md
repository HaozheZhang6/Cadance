# gmai_mmbench — GMAI-MMBench: A Comprehensive Multimodal Evaluation Benchmark Towards General Medical AI

**Venue:** NeurIPS D&B · **Year:** 2024 · **URL:** https://proceedings.neurips.cc/paper_files/paper/2024/file/ab7e02fd60e47e2a379d567f6b54f04e-Paper-Datasets_and_Benchmarks_Track.pdf · **PDF:** raw.pdf

## TL;DR
26K-item medical VQA benchmark sourced from **284 datasets / 38 imaging modalities / 18 clinical tasks / 18 departments / 4 perceptual granularities (image/box/mask/contour)**, organised as a queryable lexical tree; even GPT-4o tops out at 53.96%.

## Storyline (5-piece)
- **Problem.** Prior medical VLM evals (PathVQA, RadBench, MMMU H&M, OmniMedVQA) each cover 1–6 modalities, no department taxonomy, no perceptual granularity → reviewers can't tell if a model is "good at medicine" or just "good at chest X-rays."
- **Contribution.** (i) **GMAI-MMBench**: 26K VQA items aggregated from 284 source datasets, normalised into a single VQA schema; (ii) **lexical tree** over modality × task × department lets users define custom evaluation slices; (iii) **multi-perceptual granularity** (image-level / box / mask / contour) — first medical bench to mix all four; (iv) eval of 50 LVLMs identifying 5 systematic insufficiencies.
- **Evidence (approach).** Schema unification across 284 sources; deduplication; manual sanity check by clinical experts on a subset; lexical-tree categorical labels.
- **Experiments.** 50 LVLMs (general: GPT-4V, Claude-3, Gemini, DeepSeek-VL; medical: MedDr, LLaVA-Med, Med-Flamingo). Headline: GPT-4o = 53.96% overall; medical-specialist models often beat generalists on departments their data covers but generalise poorly outside.
- **Analysis.** 5 documented "insufficiencies": (1) modality-specific blind spots (PET, ultrasound), (2) over-reliance on textual cues vs visual evidence, (3) failure on fine-grained perception (mask/contour), (4) hallucinated clinical terms, (5) no department-level consistency.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | Cover panel: 38 modalities × 18 departments × 4 granularities | Scope claim in one shot |
| 2 | 3 | table | gap-vs-prior | Comparison vs Medical-Diff-VQA, PathVQA, MMMU H&M, etc. | Axes where GMAI-MMBench is uniquely complete |
| 3 | 5 | tree | taxonomy | Lexical tree (department → task → modality → granularity) | Customizable eval slicing |
| 4 | 7 | diagram | pipeline | 284 datasets → schema unification → dedup → lexical labels | Construction process |
| 5 | 9 | bar | headline-results | 50-LVLM ranking; GPT-4o leads at 53.96% | Headroom + generalist-vs-specialist split |

## Takeaways for BenchCAD
- **Lexical tree** as a customizable-slice mechanism is gold for a D&B paper — reviewers love being able to ask "but how does it do on flanges only?" Our cad_iso_106 family registry is already a tree; we should expose it as a queryable taxonomy.
- **Multi-granularity (image/box/mask/contour)** = orthogonal axis to task. Our analog: NL-only / image-only / NL+image / NL+image+drawing as input-modality slices.
- **5 insufficiencies framing** is a great Section 5 (Analysis) template — convert qualitative model failures into a numbered list rather than an essay.
- **Borrow** the gap-vs-prior table format: rows = competing benches, cols = orthogonal axes (#modalities, #tasks, granularities, custom slice). One ✓/✗ table kills 6 papers in the related-work.
- **Borrow** the "even SOTA tops out at <60%" headline — reviewers see immediate room for follow-up papers, increasing adoption.

## One-line citation
Chen et al. (2024). GMAI-MMBench: A Comprehensive Multimodal Evaluation Benchmark Towards General Medical AI. NeurIPS D&B 2024.
