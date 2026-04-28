# text2cadquery — Text-to-CadQuery: A New Paradigm for CAD Generation with Scalable Large Language Models

**Venue:** arXiv (Preprint, under review) · **Year:** 2025 · **URL:** https://arxiv.org/abs/2505.06507 · **PDF:** raw.pdf

## TL;DR
Augments Text2CAD's 170K NL-DeepCAD pairs with paired **CadQuery code** annotations and fine-tunes 6 open-source LLMs (124M–7B); confirms a clean scaling trend (top-1 EM 58.8 → 69.3, CD −48.6%) and argues against the custom-DSL paradigm.

## Storyline (5-piece)
- **Problem.** Existing text-to-CAD work (DeepCAD, SkexGen, Text2CAD) emits **custom command sequences** that need a hand-written decoder, can't leverage pretrained code-LM capability, and need full from-scratch training. Why bother — Python LLMs are already good at Python.
- **Contribution.** (i) **170K text↔CadQuery dataset** — extends Text2CAD by translating its DeepCAD command sequences into executable CadQuery code; (ii) **paradigm shift**: argue for natural-program output (CadQuery) over DSLs because pretrained LLMs already encode Python; (iii) **scaling study**: fine-tune 6 LLMs (CodeGPT-small 124M, GPT-2 medium 355M, GPT-2 large 774M, Gemma3-1B, Qwen2.5-3B, Mistral-7B-LoRA) and show monotonic improvement; (iv) baseline numbers + Chamfer Distance reduction.
- **Evidence (approach).** Build CadQuery translator from DeepCAD commands; verify execution + IoU equivalence; fine-tune at fixed budget; measure top-1 EM, top-k EM, exec-pass-rate, Chamfer Distance.
- **Experiments.** Smallest model (124M) trains in 58 min vs 2 days for Text2CAD's custom decoder; biggest (Mistral-7B LoRA) hits top-1 EM 69.3% (vs Text2CAD 58.8%) and reduces CD by 48.6%.
- **Analysis.** Scaling is monotonic and non-saturating up to 7B → larger LMs would help further. Authors note CadQuery scripts are *interpretable* (humans can edit them post-gen) which custom DSLs aren't — a workflow advantage.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 2 | diagram | hero | Side-by-side: custom-DSL pipeline (Text2CAD) vs direct-CadQuery pipeline (this) | Paradigm comparison in one figure |
| 2 | 4 | table | data-stats | 170K text↔CadQuery extension stats by op type and complexity | Dataset coverage |
| 3 | 6 | flowchart | pipeline | DeepCAD command → CadQuery translator → exec verify | Construction process |
| 4 | 7 | bar/table | headline-results | EM / CD across 6 LM sizes; baselines | Monotonic scaling, 7B wins |
| 5 | 9 | curve | ablation | Top-1 EM vs LM size (124M → 7B) | Clean scaling law |

## Takeaways for BenchCAD
- **CadQuery-as-output ✓** confirms our format choice. We should cite this as "the paradigm" — it shifts the framing from "yet another CAD DSL" to "code-LMs eat CAD."
- **170K text→CadQuery** is the closest competitor to our own corpus. Our cad_iso_106 (~106 families × variants) + cad_simple_ops_100k differ in: synthetic procedural origin (theirs is DeepCAD-derived), ISO compliance, multi-modal extension. We should explicitly contrast in the related-work table.
- **Scaling-curve figure** is the cleanest one-figure-headline from this paper. We should produce one for our benchmark too: model size on x-axis, exec-pass + IoU on y-axes. Reviewer-magnet.
- **Reuse their translator** if we want to reproduce DeepCAD baselines on our bench — saves us from re-implementing.
- **Borrow** the "interpretable output" argument — distinguishes us from B-rep / mesh / point-cloud benchmarks.

## One-line citation
Li et al. (2025). Text-to-CadQuery: A New Paradigm for CAD Generation with Scalable Large Language Models. arXiv:2505.06507.
