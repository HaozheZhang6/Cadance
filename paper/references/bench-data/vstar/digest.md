# vstar — V*: Guided Visual Search as a Core Mechanism in Multimodal LLMs

**Venue:** CVPR 2024 · **Year:** 2024 · **URL:** https://github.com/penghao-wu/vstar · **PDF:** raw.pdf · **arXiv:** 2312.14135

## TL;DR
Argues MLLMs lack human-like visual search and fail on small details in
high-resolution scenes; proposes V* (LLM-guided iterative search) and SEAL
(Show-sEArch-and-TelL) meta-architecture, plus V*Bench (191 high-res items)
where SEAL beats GPT-4V by 20+ pts.

## Storyline (5-piece)
- **Problem.** MLLMs fed a fixed low-resolution image cannot recover small
  object details. Existing VQA hides this because images are pre-cropped or
  resized; in real high-resolution scenes (industrial, surveillance,
  high-DPI documents) MLLMs hallucinate attributes of unseen objects.
- **Contribution.** Three pieces: (i) V*, an LLM-guided patch-recursive
  search algorithm using common-sense scene priors to localise targets;
  (ii) SEAL, a meta-architecture coupling a VQA-LLM with V* through a
  Visual Working Memory; (iii) V*Bench, 191 high-resolution VQA items
  requiring fine attribute and spatial-relation queries on small objects.
- **Evidence (approach).** Image is recursively split into 4 patches;
  the LLM scores each by relevance to the question; a queue keeps the top
  patches; located targets are tokenised into the VWM and re-fed to the
  VQA-LLM together with the global context for the final answer.
- **Experiments.** SEAL beats GPT-4V on V*Bench (75.4 vs 54.5 on attribute
  queries; 76.3 vs 56.6 on spatial). Ablation: removing V* drops to LLaVA
  baseline. Search trajectories match human fixation pattern on
  COCO-Search18 better than uniform / saliency baselines.
- **Analysis.** V* generalises across MLLM backbones; cost overhead is a
  few extra forward passes (10–20% wallclock); V*Bench is small but
  diagnostic; on broader benchmarks SEAL roughly matches the base MLLM.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | hero pipeline | hero | question + iterative search + VWM + final answer | sells the search mechanism end-to-end |
| 2 | 4 | architecture diagram | pipeline | SEAL = VQA-LLM ↔ V* ↔ VWM with target decoder | system blueprint |
| 3 | 5 | recursive patch viz | ablation | image recursively quartered, scored, top-k retained | algorithm walk-through |
| 4 | 6 | stats panel | data-stats | V*Bench composition (attribute / spatial-relation, image source) | small but targeted bench |
| 5 | 7 | results table | headline-results | SEAL vs GPT-4V / Gemini / LLaVA on V*Bench | clear margin on fine-detail tasks |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **"Small-detail bench" framing.** CAD has small parametric features
  (chamfers, fillets, hole patterns) that low-resolution renders blur; we
  can carve a "fine-detail" CAD subset analogous to V*Bench and report a
  separate accuracy.
- **Method-paper-with-bench pattern.** V* ships an algorithm plus a small
  bench. BenchCAD is bench-only, but we can include a small *baseline
  method* (e.g. multi-view-then-reason prompting) so reviewers see both
  benchmark and a reference solution.
- **VWM analogue for CAD.** Multi-view embeddings plus a parametric
  scratchpad serve the same role as V*'s working memory; we should cite V*
  when motivating the multi-view-fusion baseline in our paper.
- **Avoid V*Bench's size pitfall.** V*Bench is only 191 items; reviewers
  pushed back. BenchCAD must stay ≥1K to avoid the same critique.
- **Human-fixation comparison.** V* validates against COCO-Search18; if we
  collect expert CAD-engineer click data on parts, we can do a parallel
  comparison and ground BenchCAD's reasoning steps.

## One-line citation
Wu, P., Xie, S. (2024). *V\*: Guided Visual Search as a Core Mechanism in
Multimodal LLMs.* CVPR 2024.
