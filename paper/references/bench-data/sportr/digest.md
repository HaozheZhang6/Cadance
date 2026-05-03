# sportr — SportR: A Benchmark for Multimodal Large Language Model Reasoning in Sports

**Venue:** ICLR 2026 · **Year:** 2026 · **URL:** https://github.com/chili-lab/SportR · **PDF:** raw.pdf · **arXiv:** 2511.06499

## TL;DR
First multi-sport (5 sports, image + video) reasoning benchmark with 4,789
images, 2,052 videos, 6,841 human-authored Chain-of-Thought chains and bbox
grounding; SOTA MLLMs perform poorly (IoU 4.61 → 9.94 after SFT) — a
fundamental reasoning gap.

## Storyline (5-piece)
- **Problem.** Sports reasoning needs an intricate blend of fine-grained
  visual perception, rule-based reasoning, and visual grounding. Existing
  sports QA covers a single sport, lacks fine-grained CoT, or omits explicit
  grounding annotation, so it cannot evaluate these joint capabilities.
- **Contribution.** A pyramid framing (perception / fundamental / elite),
  with SportR pinned at the fundamental-rule level. 5 sports — basketball,
  soccer, table tennis, badminton, American football. A 7-question
  progressive QA hierarchy (Q1 infraction id → Q7 penalty prediction) plus
  6,841 human-written CoT annotations and manual bounding boxes for the
  visual-grounding sub-task.
- **Evidence (approach).** Two parts (SportsImage, SportsVideo). Each
  sample answers infraction id → foul classification → penalty prediction
  → free-form explanation → visual grounding (bbox). Multi-stage QC and
  triple-review. SFT and RL training splits are released alongside the
  evaluation set.
- **Experiments.** Closed-source (GPT-4o, Gemini, Claude) and open-source
  (Qwen2.5-VL, InternVL, LLaVA) MLLMs. Penalty-prediction accuracy < 30%
  for nearly all models; grounding IoU jumps from 4.61% baseline to 9.94%
  after SFT — still far below human.
- **Analysis.** Error pie ordering (Visual Perception > Hallucination >
  Reasoning) plus per-sport breakdown. SFT helps on shallow questions but
  the ceiling on Q5–Q7 stays low, supporting the "fundamental gap" framing.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | overview composite | hero | SportsImage + SportsVideo split with example QA chain | benchmark scope at a glance |
| 2 | 3 | pyramid + sample grid | taxonomy | 3-level pyramid (perception / fundamental / elite) plus per-sport examples | hierarchy framing |
| 3 | 4 | stats table | data-stats | sport × image / video × Q1–Q7 counts | dataset size justification |
| 4 | 6 | results table | headline-results | model × Q1–Q7 grid with SFT and RL rows | poor scores even after fine-tuning |
| 5 | 9 | error pie | failure-cases | error-type distribution per model | dominant error = Visual Perception |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **Pyramid framing is sticky and ICLR-friendly.** BenchCAD analogue:
  primitive → composition → parametric → constraint-solving, with one task
  pinned at each level.
- **Progressive QA hierarchy reusable.** Order BenchCAD's 5 tasks by
  reasoning depth (recognise → reconstruct → reason about parameters →
  edit) rather than presenting them as parallel siblings.
- **Grounding metric (bbox IoU) as separate axis from MCQ.** For CAD we can
  use parametric-IoU and surface-IoU as two grounding-style metrics that
  complement code-level exact match.
- **SFT / RL splits inside the benchmark paper.** Hanjie Chen's lab
  consistently ships SFT data; if BenchCAD provides a verified SFT split,
  we match D&B norms and reduce reviewer worry about reusability.
- **Error-pie figure.** Adopt it; one figure that conveys "model fails for
  reason X, not Y" is worth more than three accuracy bars.

## One-line citation
Xia, H., Ge, H., Zou, J., Choi, H.W., Zhang, X., Suradja, D., Rui, B.,
Tran, E., Jin, W., Ye, Z., Lin, X., Lai, C., Zhang, S., Miao, J., Chen, S.,
Tracy, R., Ordonez, V., Shen, W., Chen, H. (2026). *SportR: A Benchmark for
Multimodal Large Language Model Reasoning in Sports.* ICLR 2026.
