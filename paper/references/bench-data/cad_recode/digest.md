# cad_recode — CAD-Recode: Reverse Engineering CAD Code from Point Clouds

**Venue:** ICCV · **Year:** 2025 · **URL:** https://arxiv.org/abs/2412.14042 · **PDF:** raw.pdf

## TL;DR
Rukhovich et al. recast CAD reverse engineering as point-cloud→CadQuery Python with Qwen2-1.5B + 256-pt projector and a 1M procedurally-generated CadQuery training set, beating all prior on DeepCAD/Fusion360/CC3D and unlocking GPT-4o-driven QA & editing on the recovered code.

## Storyline (5-piece)
- **Problem.** Existing CAD reverse engineering uses method-specific token sequences trained from scratch on small hand-crafted datasets, producing outputs that aren't human-readable, can't be edited in standard CAD tools, and don't scale.
- **Contribution.** (1) CadQuery Python as the CAD sequence representation; (2) LLM-based architecture = pre-trained Qwen2-1.5B + lightweight FPS-256 + Fourier PE projector; (3) 1M procedurally generated CadQuery training set (Algo 1+2: 3-8 circle/rect+bool sketches → extrude+union+normalize+quantize+validate+dedupe).
- **Evidence (approach).** Tokens = compact 3-section CadQuery (imports / sketch planes / sketch-extrude+union); coords quantized to integer [-100,100]. NLL training, AdamW 2e-4, 100k iters, single H100 12h. Test-time: best-of-10 candidates with min-CD selection (drops IR from 4.9% to 0.4%).
- **Experiments.** Mean/Median CD + IoU (mesh voxel) + IR. Tab.1 DeepCAD: prior best CAD-SIGNet Mean CD 3.43 / IoU 77.6 / IR 0.9 → CAD-Recode (1M) **0.30 / 92.0 / 0.4** (10× CD, +14 IoU). Fusion360: 7.37/65.6 → 0.35/**87.8**. Tab.2 CC3D real-scan: 2.90/42.6 → 0.31/**74.2**. Tab.3 ablation: 160k DeepCAD → IoU 80.7 vs 160k procedural → **88.3** (procedural data is better even at fixed scale). Tab.5 SGP-Bench CAD-QA via GPT-4o: PointLLM 42.3% / CAD-SIGNet+GPT-4o 63.2% / CAD-Recode+GPT-4o **76.5%**.
- **Analysis.** Limited to sketch+extrude — no revolution/fillet/chamfer/sweep. CC3D real-world parts with high topological complexity still fail. Procedural data outperforms real DeepCAD at the same volume — challenges the "real-data-is-better" assumption.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | Existing approach (hand-crafted dataset + method-specific decoder) vs CAD-Recode (procedural + LLM + Python). | Crystallizes the "switch to executable Python + LLM" pivot. |
| 2 | 4 | figure | pipeline | Architecture: 256-pt FPS + Fourier PE projector → Qwen2-1.5B decoder predicting CadQuery code. | Compact 2-component design. |
| 3 | 6 | table | headline-results | Tab.1: DeepCAD + Fusion360 quantitative comparison vs DeepCAD/CAD-SIGNet/HNC etc. | 10× Mean CD improvement. |
| 4 | 7 | figure | case-study | Qualitative reconstruction across DeepCAD / Fusion360 / CC3D real-world inputs. | Visual evidence for cross-dataset robustness. |

CHECKED: figs/fig01_hero.png, figs/fig04_pipeline.png, figs/fig06_headline-results.png, figs/fig07_case-study.png all exist.

## Takeaways for BenchCAD
- **Procedural-data > real-data at fixed scale (Tab.3)** is direct ammunition: lets us defend our 106-family synthetic registry against "why not use ABC/DeepCAD".
- **Borrow their metric stack**: Mean+Median CD ×10³, IoU on voxelized mesh, Invalidity Ratio. Use the same scale conventions for cross-paper comparability.
- **Position vs CAD-Recode**: they cover only sketch+extrude (their explicit limitation); BenchCAD covers fillet/chamfer/loft/revolve/sweep/boolean by family. Note CC3D failures predict their model will collapse on our higher-op-arity families.
- **Steal the best-of-N+min-CD inference** as a baseline procedure for our img2cq evaluation — it's a cheap performance lift everyone uses.
- **Their training set ≠ benchmark**: they release 1M training corpus; BenchCAD is a verified IoU≥0.99 evaluation set + 5-task protocol. Frame these as orthogonal in related work.

## One-line citation
`Rukhovich, Dupont, Mallis, Cherenkova, Kacem, Aouada (2025). CAD-Recode: Reverse Engineering CAD Code from Point Clouds. ICCV.`
