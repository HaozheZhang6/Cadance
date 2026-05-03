# mm_niah — Needle In A Multimodal Haystack

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://github.com/OpenGVLab/MM-NIAH · **PDF:** raw.pdf

## TL;DR
First long-context multimodal benchmark: 12k items injecting text or image "needles" into 1k–72k-token interleaved documents (from OBELICS), probing retrieval/counting/reasoning; existing MLLMs collapse on image needles and at deeper context positions.

## Storyline (5-piece)
- **Problem.** MLLMs are claimed long-context capable but no benchmark tests *multimodal* long-context — SEED-Bench-2/BLINK are short, MVBench is video-only. Need to evaluate long interleaved image-text comprehension.
- **Contribution.** MM-NIAH adapts text NIAH to multimodal: concatenate OBELICS docs into 1k–72k token haystacks, inject text or image needles at controllable depth, and ask three task types — retrieval (return needle content), counting (multi-needle), reasoning (combine cues across needles).
- **Evidence (approach).** Synthetic but principled: deterministic needle insertion with depth-buckets enables 2-D heatmaps (context length × depth). Two needle modalities (text vs image) and three task types yield a 2 × 3 grid. ~12k evaluation samples.
- **Experiments.** Evaluate Gemini-1.5, GPT-4V/4o, Claude-3, InternVL-1.5, plus open MLLMs. Image-needle accuracy far below text-needle; counting hardest; performance decays with depth and context length; image-text-interleaved pretraining does NOT consistently help.
- **Analysis.** Per-position heatmaps reveal classic "lost-in-the-middle" pattern but worse for image needles; many models hit floor when context >32k tokens; reasoning >> counting >> retrieval in difficulty per-task.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 2 | comparison | gap-vs-prior | MM-NIAH vs SEED-Bench-2 / MVBench example layouts. | Establishes long multimodal niche. |
| 2 | 4 | qualitative | examples | Six task examples covering retrieval/counting/reasoning × text/image needle. | Defines the 2×3 task grid. |
| 3 | 5 | flow diagram | pipeline | OBELICS docs → concat → needle injection at depth d. | Construction recipe; deterministic. |
| 4 | 7 | bar/table | headline-results | Per-model accuracy across tasks and lengths. | Image needles much worse than text; large drop at long ctx. |
| 5 | 8 | heatmap grid | failure-cases | Context-length × depth accuracy heatmaps per model. | Lost-in-middle + image-needle blind spots visible. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow the controllable-axis idea: in CAD, vary "part complexity" (feature count) × "image resolution / view count" and produce a 2-D heatmap of accuracy — analogue of context-length × depth.
- Borrow synthetic injection at controlled positions: for CAD bench, controllably perturb a single dimension or hole position and ask if model still recovers the spec — measures localized sensitivity.
- Borrow heatmap visualization style (per-model, per-axis) — instant signature figure for D&B reviewers.
- Borrow distinction between modality-specific task drops: in CAD, separate "view-only" vs "view+JSON" inputs; show modality dropout impact.
- Avoid: their needle-insertion evaluation is template; for CAD we need real geometric items, no shortcut to synthetic concat.

## One-line citation
Wang et al., "Needle In A Multimodal Haystack," NeurIPS 2024 Datasets & Benchmarks.
