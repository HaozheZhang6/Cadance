# histcad — HistCAD: Geometrically Constrained Parametric History-based CAD Dataset

**Venue:** arXiv (submitted IEEE) · **Year:** 2026 · **URL:** arXiv 2602.19171 · **PDF:** raw.pdf

## TL;DR
160,501 parametric CAD modeling sequences in a flat constraint-aware format with 10 geometric constraint types, five aligned modalities (sequences, B-rep STEP, native PRT, multi-view renders, LLM-generated text), plus 8,141 industrial Siemens-NX parts — designed for editable, constraint-compliant text-to-CAD generation.

## Storyline (5-piece)
- **Problem.** Existing CAD datasets fail on (1) absent explicit geometric constraints (DeepCAD, Text2CAD), (2) academic-only complexity (no industrial parts), (3) shallow text annotations (no functional intent), (4) hierarchical sketch nesting that bloats tokens.
- **Contribution.** HistCAD: flat constraint-aware modeling sequence with 10 explicit constraints (coincident, parallel, perpendicular, horizontal, vertical, tangent, equal, concentric, fix, normal); 5 aligned modalities; HistCAD-Industrial subset of 8,141 NX parts with rotated extrusions; AM_HistCAD LLM-driven annotation module producing 3 text types (process / shape / functional intent).
- **Evidence (approach).** Three-stage integration of DeepCAD + SketchGraphs + Fusion 360 Gallery: (i) decompose face-loop into primitives, (ii) symmetric-difference flatten, (iii) align to SketchGraphs constraints. NX parts parsed with rotated extrusions. AM_HistCAD: extract → translate to NL → guided LLM generates 3 annotation types.
- **Experiments.** Token efficiency: HistCAD avg 358.87 (no constraints) / 476.11 (with) vs DeepCAD 1878.65 vs Text2CAD 560.24 (Qwen3-0.6B tokenizer). Chamfer Distance 7.59 (HistCAD) ≈ 7.76 (DeepCAD) < 10.02 (Text2CAD). Constraint-aware editing in FreeCAD preserves tangency/concentricity that constraint-free variant breaks. Text-driven generation robustness improves with flat representation.
- **Analysis.** Constraint encoding adds 32.7% sequence length but enables true parametric editing. Industrial subset boosts performance on real-world cases without hurting academic benchmarks. Constraint-frequency table shows coincident (27.3%) + horizontal (21.7%) dominate.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|------|------|
| 2 | 2 | sample grid | hero | Random gallery of HistCAD designs spanning academic + industrial | Visual diversity, industrial complexity |
| 4 | 4 | comparison table | taxonomy | DeepCAD vs Text2CAD vs HistCAD on 5 features (constraints, flat, etc.) | Why HistCAD beats prior representations |
| 5 | 5 | constraint freq + tokens | data-stats | Constraint type distribution + token-count density curves | Sequence efficiency and constraint coverage |
| 6 | 6 | qualitative recon | headline-results | Recon vs Text2CAD vs DeepCAD vs ABC GT on shared subset | Geometric fidelity advantage |
| 9 | 9 | editing demo | ablation | FreeCAD edits with vs without constraints | Constraint-aware editability — practical payoff |

## Takeaways for BenchCAD (NeurIPS 2026 D&B paper, CAD-code-gen benchmark)
- Borrow: HistCAD is the closest contemporary peer — must explicitly position BenchCAD against it. The differentiation needs to be code-gen evaluation harness, not just dataset.
- Borrow: token-count distribution chart (HistCAD Fig. 2) is the right way to argue compactness — replicate for our family-based programs.
- Borrow: Chamfer-Distance vs ABC GT is the standard geometric fidelity metric; reuse for executable scoring.
- Contrast: HistCAD focuses on representation quality, not on benchmarking generators. BenchCAD should emphasize evaluation-suite contributions: held-out test programs, exec-then-IoU scoring, per-skill breakdown.
- Avoid: claiming "first" constraint-aware dataset — HistCAD has staked that flag with 10 constraint types; compete on scale, code-execution, or program diversity instead.

## One-line citation
Dong et al., "HistCAD: Geometrically Constrained Parametric History-based CAD Dataset," arXiv 2602.19171, 2026.
