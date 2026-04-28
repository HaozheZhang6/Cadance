# query2cad — Query2CAD: Generating CAD models using Natural Language Queries

**Venue:** arXiv · **Year:** 2024 · **URL:** https://arxiv.org/abs/2406.00144 · **PDF:** raw.pdf

## TL;DR
Zero-training NL→FreeCAD-macro pipeline: GPT-4-Turbo generates a Python macro, BLIP2-VQA scores the rendered isometric, and a 3-iteration self-refinement loop (with HITL fallback) lifts first-attempt success 53.6% → +23.1%.

## Storyline (5-piece)
- **Problem.** Earlier 3D-gen work (mesh/voxel/point-cloud diffusion, image-to-3D) gives lossy meshes that are useless for manufacturing. CAD-specific generation needs precise parametric output; no end-to-end NL→CAD pipeline existed without supervised data.
- **Contribution.** (i) **Query2CAD** — training-free framework: LLM generates a FreeCAD Python macro from NL → execute → render isometric → BLIP2 generates a caption → VQA score against original NL query; if below threshold, refine. (ii) Self-refinement loop runs up to 3 iterations. (iii) HITL fallback to handle BLIP2 false negatives. (iv) Custom NL→CAD eval set covering most FreeCAD ops (extrude, revolve, fillet, chamfer, cut, etc.).
- **Evidence (approach).** No supervised training. LLM acts as both generator and refiner; BLIP2 acts as VQA grader. Threshold-based stopping. The contribution is the loop architecture + the prompting protocol.
- **Experiments.** GPT-4 Turbo gets 53.6% first-attempt success. Refinement adds +23.1%. Most of the lift comes from iteration 1; iterations 2–3 plateau (diminishing returns).
- **Analysis.** Plateau = LLM keeps producing the same wrong macro because BLIP2 feedback is too generic. HITL kicks in at false-negative cases. Ops with multiple constraints (chamfer + fillet on same edge) consistently fail.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | diagram | hero | NL → LLM → FreeCAD macro → render → BLIP2-VQA → refine | The end-to-end loop in one diagram |
| 2 | 3 | flowchart | pipeline | Refinement loop with threshold + HITL fallback branch | Stopping logic |
| 3 | 5 | examples | data-stats | Op-coverage examples: extrude, revolve, fillet, etc. | Eval set composition |
| 4 | 7 | bar | headline-results | First-attempt vs after-refinement success per op type | +23% delta concentrated on iter 1 |

## Takeaways for BenchCAD
- **Self-refinement is a free baseline** — for BenchCAD, run prompted models with no-refine vs 3-iter render-feedback refine to show the floor and ceiling.
- **VQA-as-grader is unreliable** — BLIP2 false negatives motivate why we use deterministic geometry metrics (IoU + CD + exec-pass) rather than caption matching.
- **Op-coverage eval slice** matches our family×operation grid; we should report per-op breakdown like Query2CAD does.
- **Avoid:** their <100-prompt eval set is too small to distinguish models; Methodologically, lean on our 1.4k subset and 17.8k full bench.
- **Borrow** the 3-iter plateau finding — useful negative result for the "is more inference-time compute the answer?" debate (cf. cadrille's Dr.CPPO that adds RL for this exact reason).

## One-line citation
Badagabettu et al. (2024). Query2CAD: Generating CAD models using Natural Language Queries. arXiv:2406.00144.
