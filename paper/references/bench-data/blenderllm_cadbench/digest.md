# blenderllm_cadbench — BlenderLLM: Training Large Language Models for Computer-Aided Design via Self-Improvement (with CADBench)

**Venue:** arXiv · **Year:** 2024 · **URL:** https://arxiv.org/abs/2412.14203 · **PDF:** raw.pdf

## TL;DR
Pairs a **BlendNet** SFT corpus with a 200-instance **CADBench** eval suite for NL→Blender-Python script generation; iterative self-improvement on Qwen2.5-Coder-7B beats GPT-4o / Claude-3.5 on functional correctness despite being 100× smaller.

## Storyline (5-piece)
- **Problem.** Existing CAD-LLM pipelines either need expensive custom DSLs (DeepCAD command sequences) or hit a wall because (a) input forms are too complex, (b) high-quality NL↔CAD pairs are scarce, (c) no domain-specific eval suite exists. CAD scripts are also hard to render-and-judge automatically.
- **Contribution.** Three artifacts: (i) **BlendNet** SFT/RL corpus (12k NL prompts → Blender-Python scripts auto-checked by render); (ii) **CADBench** (500 simulated + 200 forum-sourced eval items, 4 difficulty tiers, executes in Blender with rule-based grading on functionality + accuracy); (iii) **BlenderLLM**: Qwen2.5-Coder-7B SFT then self-improvement loop where the model regenerates failed cases with feedback on render/error logs.
- **Evidence (approach).** Self-improvement loop: model proposes script → headless Blender executes → if render fails, error log is returned and model retries; successful renders are added back to training data. Iterates 3 rounds.
- **Experiments.** Compared against GPT-4o, GPT-4-Turbo, Claude-3.5-Sonnet, Gemini-1.5-Pro, BlenderGPT, o1-Preview on CADBench. BlenderLLM-7B reaches the highest Functionality + Accuracy combined score, particularly on hard items where SOTA proprietary models fail to generate executable code.
- **Analysis.** Failure-class breakdown: most prior models trip on (a) Blender API hallucination (wrong attribute names), (b) misjudged dimensions (units/orientation), (c) operation order. Self-improvement narrows (a) and (b) but barely helps (c) — order errors need symbolic feedback the render alone can't provide.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | NL prompt → BlenderLLM script → rendered chair / burger / desk-lamp examples | The text-to-3D loop and three demo categories |
| 2 | 3 | table+text | taxonomy | 4 difficulty tiers × functionality vs accuracy split | Eval axis structure |
| 3 | 5 | diagram | pipeline | Self-improvement loop: render → error → retry → SFT | Closed-loop training on Blender execution |
| 4 | 7 | table | headline-results | CADBench scores: BlenderLLM vs 6 SOTA models | 7B-SFT beats GPT-4o on functional eval |
| 5 | 9 | grid | case-study | Side-by-side renders for shared prompts (chair, burger, lamp) | Where SOTA fails and BlenderLLM succeeds |

## Takeaways for BenchCAD
- **Two-tier eval (simulated + forum-sourced)** is a clean way to defend "real-world coverage" without fully manual curation — directly translatable to our cad_iso_106 (synthetic) + 17.8k bench (curated) split.
- **Render-as-grader** removes annotator subjectivity for functional correctness; we can adopt for our CadQuery exec-pass + IoU eval, but should add operation-order checks the render misses.
- **Self-improvement loop** is a free "ablation knob" for our paper if we want to demonstrate value of our data beyond SFT.
- **Avoid:** their 200 forum items are too small to be a stable benchmark — reviewers will note variance. Our 1.4k curated subset is the right scale.
- **Borrow** the failure-class taxonomy (API hallucination / dimension / operation order) — directly applicable to CadQuery and gives reviewers concrete failure modes.

## One-line citation
Du et al. (2024). BlenderLLM: Training Large Language Models for Computer-Aided Design via Self-Improvement. arXiv:2412.14203.
