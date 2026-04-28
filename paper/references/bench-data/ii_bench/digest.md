# ii_bench — II-Bench: An Image Implication Understanding Benchmark for Multimodal Large Language Models

**Venue:** NeurIPS 2024 D&B · **Year:** 2024 · **URL:** https://huggingface.co/datasets/m-a-p/II-Bench · **PDF:** raw.pdf

## TL;DR
1,222 metaphor-rich images (illustrations/comics/posters) with 1,434 6-option MCQs probing higher-order implication understanding; best MLLM 74.8% vs human avg 90% / max 98%, with abstract Art/Psychology domains hardest.

## Storyline (5-piece)
- **Problem.** MLLM benches target literal recognition + factual VQA; missing higher-order perception — symbolic, metaphorical, emotional content like artwork, comics, posters where meaning is implicit.
- **Contribution.** II-Bench, 1,222 images / 1,434 MCQs across 6 domains (Life, Art, Society, Psychology, Environment, Other) and 7 image types (illustration, meme, poster, multi/single-panel comic, logo, painting); each item has rhetorical-device annotation (metaphor, symbolism, contrast, …) and difficulty/sentiment labels.
- **Evidence (approach).** 20,150 raw images crawled → image-similarity dedup → OCR-area filter → human-curation discarding non-implicational; 50 undergrad annotators write 1–3 questions each with 6 options, 5-reviewer consensus required.
- **Experiments.** 20 MLLMs (open + closed). Top: GPT-4o 74.8; humans avg 90, max 98. Closed-vs-open gap is just ~1% at the top — InternVL-Chat-1.5 close to GPT-4o. Worst domains: Art, Psychology.
- **Analysis.** Adding sentiment-polarity hints to prompt boosts most models 2–5 pts → models lack innate emotional grounding. Failure analysis shows literal misreadings, missed cultural context, rhetorical-device confusion.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|--------------------------|----------------|
| 1 | 1 | qualitative | hero | A metaphor image; humans 90% / MLLMs 74.8% with one item. | Visualizes the gap and frames "implication" task. |
| 2 | 2 | pie chart | taxonomy | Composition of II-Bench by domain + image type. | Diversity across 6 domains and 7 image types. |
| 3 | 4 | gallery | data-stats | Six representative images, one per domain. | Concrete examples per category. |
| 4 | 5 | stats table | data-stats | Difficulty / sentiment / rhetoric counts. | Fine-grained metadata; balanced splits. |
| 5 | 7 | results table | headline-results | 20 MLLMs accuracy by domain + difficulty + emotion. | GPT-4o 74.8; abstract domains hardest. |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- Borrow rich metadata per item (rhetoric/sentiment/difficulty); for CAD use family/feature-count/symmetry/manufacturability tags so scores can slice many ways.
- Borrow "prompt-with-hint" ablation: ablate giving the model partial info (e.g., feature list) → if accuracy jumps, the bottleneck is recognition not reasoning. Powerful diagnostic.
- Borrow human topline 5-reviewer consensus; for CAD that means 3 CAD engineers re-implementing each part to lock GT.
- Borrow domain stratification chart (pie + per-domain bars); the visual reads instantly.
- Avoid: 6-option MCQ format — not transferable to CAD generation; stick to free-form CadQuery + geometric metric.

## One-line citation
Liu et al., "II-Bench: An Image Implication Understanding Benchmark for MLLMs," NeurIPS 2024 Datasets & Benchmarks.
