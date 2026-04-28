# spatialeval — Is A Picture Worth A Thousand Words? Delving Into Spatial Reasoning for VLMs

**Venue:** NeurIPS 2024 · **Year:** 2024 · **URL:** https://github.com/jiayuww/SpatialEval · **PDF:** raw.pdf

## TL;DR
SpatialEval is a 4-task (Spatial-Map, Maze-Nav, Spatial-Grid, Spatial-Real) benchmark with redundant text/image/text+image input modes; reveals that VLMs often perform at random and underperform their LLM backbones when given only images, even when text alone solves the task.

## Storyline (5-piece)
- **Problem.** Spatial reasoning is fundamental but VLM evaluation conflates it with general VQA; no benchmark isolates spatial skill while controlling for modality.
- **Contribution.** SpatialEval — 4 tasks each rendered in three input modalities (TQA text-only, VQA image-only, VTQA both with redundant info) so the same question is answerable from either channel.
- **Evidence (approach).** Spatial-Map (named-location pairwise relations), Maze-Nav (ASCII maze + image), Spatial-Grid (5×5 animal grid), Spatial-Real (DCI long-caption real images). Configurable & scalable to avoid leakage. Multiple-choice, accuracy metric, single-prompt CoT instruction.
- **Experiments.** Evaluate ~20 LLMs + VLMs (Phi, LLaMA-2/3, Mistral, Vicuna, Yi-34B, Bunny, CogVLM, InstructBLIP, LLaVA-1.6, Qwen-VL, GPT-4V/4o, Gemini Pro, Claude 3 Opus). Many sit at random in vision-only mode; Spatial-Grid hardest gap (LLaMA-3 71.9% TQA vs LLaVA 47.1% VQA).
- **Analysis.** (1) VLMs sometimes worse than random; (2) VLMs underperform LLM backbone when only image given; (3) when text + image both given, VLMs ignore the image; (4) VLMs on TQA outperform same-backbone LLMs — multimodal training helps the language path.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 3 | 3 | Maze-Nav prompts | taxonomy | TQA/VQA/VTQA versions of the same maze question | Three-modality prompt design |
| 4 | 4 | Spatial-Grid + Real | taxonomy | Grid prompts and Real-image counting question | Task variety from synthetic to natural |
| 6 | 6 | bar chart | headline-results | Per-model accuracy on Spatial-Map / Maze-Nav / Spatial-Grid | Many VLMs at or below random |
| 7 | 7 | radar/spider plot | radar-comparison | (VLM, LLM-backbone) pairs across tasks | VLM vs LLM-backbone gap, often negative |
| 8 | 8 | modality bars | ablation | TQA vs VQA vs VTQA per model | Adding image rarely helps; redundant text dominates |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: triple-modality framing (image-only / text-spec only / both) is the single most powerful experimental design here — directly reusable as CAD code-gen evaluated under image only / textual spec only / multi-modal.
- Borrow: report VLM-vs-LLM-backbone delta — exposes whether vision actually contributes to CAD code generation, or if the LLM is hallucinating from a textual schema.
- Contrast: SpatialEval is multiple-choice; CAD code-gen is generative — adapt the modality control concept but use IoU/match metrics instead of MC-accuracy.
- Avoid: random-guess line on a 4-option MC is reviewer-friendly but doesn't transfer; for CAD use "empty program" or "copy-input" baselines to anchor.
- Borrow: include a "redundant text" variant that gives the answer in words to detect models that ignore the image — useful failure mode.

## One-line citation
Wang et al., "Is A Picture Worth A Thousand Words? Delving Into Spatial Reasoning for Vision Language Models," NeurIPS 2024.
