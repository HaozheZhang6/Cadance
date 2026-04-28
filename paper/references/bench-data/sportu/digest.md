# sportu — SPORTU: A Comprehensive Sports Understanding Benchmark for Multimodal Large Language Models

**Venue:** ICLR 2025 · **Year:** 2025 · **URL:** https://github.com/chili-lab/SPORTU · **PDF:** raw.pdf · **arXiv:** 2410.08474

## TL;DR
Two-part sports benchmark (SPORTU-text 900 MCQ + SPORTU-video 1,701 slow-mo
clips × 12,048 QA across 7 sports); GPT-4o tops text at 71% but only 57.8%
on hard video; Qwen2-VL-72B 70.94% overall — deep sports reasoning still
unsolved.

## Storyline (5-piece)
- **Problem.** Existing sports QA is text-only or single-sport video, with
  no multi-level reasoning hierarchy. Cannot evaluate MLLMs' ability to
  apply rules to fine-grained slow-motion actions where a foul lasts under
  one second.
- **Contribution.** SPORTU = SPORTU-text (900 MCQ + human-written
  explanation for rule comprehension) + SPORTU-video (1,701 slow-motion
  clips, 7 sports, 12,048 QA across 3 difficulty levels easy / medium /
  hard, plus 300 multi-camera-angle clips for viewpoint robustness).
- **Evidence (approach).** Slow-motion is critical because most fouls
  involve sub-second actions invisible at real-time speed. Difficulty
  tiered: easy = no domain knowledge, medium = some, hard = deep rule
  comprehension. Multi-angle subset reuses the same question over multiple
  camera angles to expose viewpoint sensitivity.
- **Experiments.** 4 LLMs on text (GPT-4o 71%, Claude-3.5-Sonnet,
  Gemini-1.5-Pro, LLaMA-3.1) using zero-shot and few-shot ± CoT; 14 MLLMs
  on video. Qwen2-VL-72B = 70.94 overall but only 44.12 on hard;
  Claude-3.5-Sonnet best on hard with 52.57%.
- **Analysis.** CoT *hurts* on hard video — Claude drops 52.57 → 39.32 when
  asked to reason first then answer, indicating models cannot sustain
  reasoning chains. Error pie shows Question-Understanding dominates.
  Multi-camera-angle subset shows accuracy varies by viewpoint by up to
  15 pts on the same question.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | split overview | hero | text vs video pillars + sample QA | dual-component framing |
| 2 | 4 | example grid | taxonomy | text MCQ + video easy / medium / hard examples | shows difficulty tiering |
| 3 | 5 | stats table | data-stats | per-sport clip counts and QA counts | data scale and balance |
| 4 | 6 | results table | headline-results | MLLM × difficulty grid for video MCQ | hard-column collapse |
| 5 | 8 | error pie | failure-cases | error-type distribution from manual labelling | Question Understanding dominates |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **Difficulty tiering inside one task** (easy / medium / hard) already
  aligns with our easy / medium / hard family params. Surface as separate
  columns in the main results table so the "hard column" punchline lands.
- **CoT-hurts finding** is reusable. Test CoT on CAD codegen and report
  whether it helps; if it hurts, that itself is a publishable surprise.
- **Multi-view robustness subset.** Analogue: render 4 views vs 1 view of
  the same part and check accuracy delta per task — a "view ablation"
  subset that costs almost nothing to add.
- **Avoid one-shot accuracy as headline.** SPORTU's main table is dense
  (3 difficulty × 14 model); we should mirror but limit to ≤30 models for
  legibility, and bold best-per-group not best-overall.
- **No separate Limitations section** (Hanjie Chen style). Embed
  limitations at subsection ends as future work; keeps focus on contribution.

## One-line citation
Xia, H., Yang, Z., Zou, J., Tracy, R., Wang, Y., Lu, C., Lai, C., He, Y.,
Shao, X., Xie, Z., Wang, Y.-F., Shen, W., Chen, H. (2025).
*SPORTU: A Comprehensive Sports Understanding Benchmark for Multimodal
Large Language Models.* ICLR 2025.
