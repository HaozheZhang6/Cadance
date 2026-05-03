# BenchCAD — 60-paper benchmark survey candidates

Read date: 2026-04-27 · Track target: NeurIPS 2026 D&B

## A. CAD / mechanical / parametric (~10) [10]
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 1 | text2cad | Text2CAD: Generating Sequential CAD Designs from Beginner-to-Expert Level Text Prompts | NeurIPS D&B (Spotlight) | 2024 | https://openreview.net/forum?id=5k9XeHIK3L | Text-to-parametric CAD, 170k models w/ 660k captions; direct competitor | [have] |
| 2 | cad_coder | CAD-Coder: Open-Source VLM for CAD Code Generation | NeurIPS / IDETC | 2025 | https://arxiv.org/abs/2505.19713 | Img→CadQuery 163k pairs; closest in spirit to BenchCAD | [have] |
| 3 | cad_recode | CAD-Recode: Reverse Engineering CAD Code from Point Clouds | ICCV | 2025 | https://openaccess.thecvf.com/content/ICCV2025/papers/Rukhovich_CAD-Recode_Reverse_Engineering_CAD_Code_from_Point_Clouds_ICCV_2025_paper.pdf | Procedural CAD-as-code; benchmark for PC→Python | [have] |
| 4 | cadrille | cadrille: Multimodal CAD Reconstruction with RL | ICLR | 2026 | https://arxiv.org/abs/2505.22914 | Multimodal CAD recon w/ RL; trained on procedural CAD-Recode set | [have] |
| 5 | cadevolve | CADEvolve: Creating Realistic CAD via Program Evolution | arXiv | 2026 | https://arxiv.org/abs/2602.16317 | Evolutionary CAD code search; recent CAD-LLM lineage | [have] |
| 6 | cadcodeverify | CADCodeVerify / CADPrompt: Evaluating CAD Code Generation | ICLR | 2025 | https://proceedings.iclr.cc/paper_files/paper/2025/file/81a934cd364e18ea6fdeaf57a93c17d4-Paper-Conference.pdf | First quantitative VLM CAD-code eval (CadQuery) | [have] |
| 7 | cadtalk | CADTalk: An Algorithm and Benchmark for Semantic Commenting of CAD Programs | CVPR | 2024 | https://arxiv.org/abs/2311.16703 | CAD-program semantic labels; 5,288 + 45 programs | [priority] |
| 8 | text2cadquery | Text-to-CadQuery: Scalable Large-Model CAD Generation | arXiv | 2025 | https://arxiv.org/abs/2505.06507 | Qwen-3B fine-tuned on CadQuery; benchmark variant | [stretch] |
| 9 | blenderllm_cadbench | BlenderLLM + CADBench: Self-Improvement LLM for CAD Scripts | arXiv | 2024 | https://arxiv.org/abs/2412.14203 | 500 simulated + 200 forum CAD-script eval samples | [priority] |
| 10 | query2cad | Query2CAD: Generating CAD Models using Natural Language Queries | arXiv | 2024 | https://arxiv.org/abs/2406.00144 | NL→FreeCAD macros; baseline competitor | [stretch] |

## B. 3D / mesh / shape generation benchmarks (~10)
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 12 | objaverse_xl | Objaverse-XL: A Universe of 10M+ 3D Objects | NeurIPS D&B | 2023 | https://proceedings.neurips.cc/paper_files/paper/2023/file/70364304877b5e767de4e9a2a511be0c-Paper-Datasets_and_Benchmarks.pdf | Largest 3D-asset corpus; reference for 3D dataset scope | [priority] |
| 13 | cap3d | Scalable 3D Captioning with Pretrained Models (Cap3D) | NeurIPS D&B | 2023 | https://openreview.net/forum?id=jUpVFjRdUV | 660k 3D-text pairs; pipeline template | [stretch] |
| 14 | mv2cyl | MV2Cyl: Reconstructing 3D Extrusion Cylinders from Multi-View Images | NeurIPS | 2024 | https://arxiv.org/abs/2406.10853 | Multi-view extrusion-recon eval setup | [stretch] |
| 15 | msqa_msr3d | MSR3D: Multi-modal Situated Reasoning in 3D Scenes (MSQA) | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/feaeec8ec2d3cb131fe18517ff14ec1f-Paper-Datasets_and_Benchmarks_Track.pdf | 251k 3D-scene QA; multimodal eval template | [priority] |
| 16 | spatialrgpt | SpatialRGPT + SpatialRGBT-Bench: Grounded Spatial Reasoning VLMs | NeurIPS | 2024 | https://papers.nips.cc/paper_files/paper/2024/file/f38cb4cf9a5eaa92b3cfa481832719c6-Paper-Conference.pdf | 3D-grounded VLM benchmark | [priority] |
| 17 | spatialeval | Is A Picture Worth A Thousand Words? SpatialEval Benchmark | NeurIPS | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/89cc5e613d34f90de90c21e996e60b30-Paper-Conference.pdf | Modality-controlled spatial-reasoning bench | [priority] |
| 18 | gsr_bench | GSR-Bench: Grounded Spatial Reasoning Evaluation via MLLMs | NeurIPS | 2024 | https://arxiv.org/abs/2406.13246 | Grounded spatial-reasoning eval | [stretch] |
| 19 | care_pd | CARE-PD: Multi-Site Anonymized Clinical Dataset for Parkinson's Gait | NeurIPS D&B | 2025 | https://arxiv.org/abs/2510.04312 | 3D-mesh dataset structure example | [stretch] |
| 20 | histcad | HistCAD: Geometrically Constrained Parametric History CAD Dataset | arXiv | 2026 | https://arxiv.org/abs/2602.19171 | History-based parametric CAD dataset; recent | [stretch] |
| 21 | mindjourney | MindJourney: Test-Time Scaling with World Models for Spatial Reasoning | NeurIPS | 2025 | https://arxiv.org/abs/2507.12508 | World-model spatial bench | [stretch] |

## C. Code-generation benchmarks (~10)
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 22 | autocodebench | AutoCodeBench: Auto-generating Code Benchmarks | ICLR | 2026 | https://arxiv.org/abs/2508.09101 | Auto-gen code eval; methodology template | [have] |
| 23 | livecodebench | LiveCodeBench: Holistic Contamination-Free Code Eval | ICLR | 2025 | https://openreview.net/forum?id=chfJJYC3iL | Time-segmented code eval; contamination defense | [priority] |
| 24 | bigcodebench | BigCodeBench: Code Generation w/ Diverse Function Calls | ICLR | 2025 | https://openreview.net/forum?id=YrycTjllL0 | 1,140 multi-tool tasks; complex-instruction eval | [priority] |
| 25 | scicode | SciCode: A Research Coding Benchmark Curated by Scientists | NeurIPS D&B | 2024 | https://openreview.net/forum?id=ADLaALtdoG | 338 scientific subproblems; expert-curated | [priority] |
| 26 | swebench_pro | SWE-Bench Pro: Long-Horizon Software Engineering | OpenReview | 2025 | https://openreview.net/forum?id=9R2iUHhVfr | Real-world repo-level SWE eval | [priority] |
| 27 | spider2 | Spider 2.0: Real-World Enterprise Text-to-SQL | ICLR (Oral) | 2025 | https://openreview.net/forum?id=XmProj9cPs | 632 enterprise SQL workflows; structured-code eval | [priority] |
| 28 | repobench | RepoBench: Repository-Level Code Auto-Completion | ICLR | 2024 | https://openreview.net/forum?id=pPjZIOuQuF | Repo-level code completion eval | [stretch] |
| 29 | codemmlu | CodeMMLU: Multi-Task Code Understanding Benchmark | OpenReview | 2024 | https://openreview.net/forum?id=CahIEKCu5Q | 20k MCQs across code tasks | [stretch] |
| 30 | codesense | CodeSense: Benchmark for Code Semantic Reasoning | ICLR | 2026 | https://arxiv.org/abs/2506.00750 | Real-world code-reasoning trace bench | [priority] |
| 31 | convcodeworld | ConvCodeWorld: Benchmarking Conversational Code Gen | ICLR | 2025 | https://proceedings.iclr.cc/paper_files/paper/2025/file/6091f2bb355e960600f62566ac0e2862-Paper-Conference.pdf | Multi-turn feedback code-eval | [stretch] |

## D. VLM / MLLM evaluation (~10)
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 32 | mmmu_pro | MMMU-Pro: More Robust Multi-discipline Multimodal Bench | ACL | 2025 | https://openreview.net/forum?id=2jTdHYuguF | Robust multi-discipline VLM eval | [priority] |
| 33 | charxiv | CharXiv: Realistic Chart Understanding in MLLMs | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/cdf6f8e9fd9aeaf79b6024caec24f15b-Paper-Datasets_and_Benchmarks_Track.pdf | 2,323 chart QA; gold-standard reasoning bench | [priority] |
| 34 | math_v | MATH-V: Multimodal Math-Vision Benchmark | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/ad0edc7d5fa1a783f063646968b7315b-Paper-Datasets_and_Benchmarks_Track.pdf | 3,040 math+vis problems; 16 disciplines | [priority] |
| 35 | ii_bench | II-Bench: Image Implication Understanding for MLLMs | NeurIPS D&B | 2024 | https://openreview.net/forum?id=iEN2linUr8 | High-order image-implication eval | [stretch] |
| 36 | mm_niah | MM-NIAH: Needle In A Multimodal Haystack | NeurIPS D&B | 2024 | https://arxiv.org/abs/2406.07230 | Long multimodal-doc eval | [stretch] |
| 37 | mllm_compbench | MLLM-CompBench: Comparative Reasoning for MLLMs | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/hash/32923dff09f75cf1974c145764a523e2-Abstract-Datasets_and_Benchmarks_Track.html | Pairwise visual-comparison bench | [stretch] |
| 38 | mega_bench | MEGA-Bench: Scaling Multimodal Eval to 500+ Tasks | ICLR | 2025 | https://openreview.net/forum?id=2rWbKbmOuM | Massive-scale MLLM task suite | [priority] |
| 39 | visual_cot | Visual CoT: Multi-Modal CoT Reasoning Dataset | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/hash/0ff38d72a2e0aa6dbe42de83a17b2223-Abstract-Datasets_and_Benchmarks_Track.html | 438k CoT visual reasoning pairs | [stretch] |
| 40 | infinity_chat | Infinity-Chat: Open-Ended Generation Benchmark | NeurIPS D&B (Best) | 2025 | https://arxiv.org/abs/2510.22954 | 26k queries / 31k human-annot; methodology gold standard | [have] |
| 41 | gmai_mmbench | GMAI-MMBench: Comprehensive Medical Multimodal Eval | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/ab7e02fd60e47e2a379d567f6b54f04e-Paper-Datasets_and_Benchmarks_Track.pdf | Domain-specific MLLM eval template | [stretch] |

## E. Visual / spatial / multi-image reasoning (~8)
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 42 | blink | BLINK: MLLMs Can See but Not Perceive | ECCV | 2024 | https://arxiv.org/abs/2404.12390 | 14 perception tasks, 3,807 MCQs; visual-prompt bench | [priority] |
| 43 | mmsi_bench | MMSI-Bench: Multi-Image Spatial Intelligence | ICLR | 2026 | https://arxiv.org/abs/2505.23764 | Multi-image spatial reasoning | [have] |
| 44 | mmiu | MMIU: Multimodal Multi-Image Understanding | OpenReview | 2024 | https://openreview.net/forum?id=WsgEWL8i0K | Multi-image LVLM eval; spatial-heavy | [priority] |
| 45 | sportr | SportR: Sports Reasoning Benchmark | ICLR | 2026 | https://arxiv.org/abs/2511.06499 | Domain reasoning bench template | [have] |
| 46 | sportu | SPORTU: Sports Understanding Benchmark | ICLR | 2025 | https://arxiv.org/abs/2410.08474 | Multi-image temporal reasoning template | [have] |
| 47 | vstar | V*: Guided Visual Search Benchmark | CVPR | 2024 | https://arxiv.org/abs/2312.14135 | Long-context visual search; high-res VQA | [stretch] |
| 48 | spatialqa | SpatiaLQA: Spatial Logical Reasoning for VLMs | arXiv | 2026 | https://arxiv.org/abs/2602.20901 | 9,605 indoor scene QA; logical-spatial bench | [stretch] |
| 49 | ego3d_bench | Ego3D-Bench: Egocentric Multi-View VLM Bench | arXiv | 2025 | https://arxiv.org/abs/2509.06266 | Outdoor multi-view VLM eval | [stretch] |

## F. D&B paper structure templates (~7)
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 50 | gaia | GAIA: A Benchmark for General AI Assistants | ICLR | 2024 | https://openreview.net/forum?id=fibxvahvs3 | 466 multi-tool QA; gold methodology template | [priority] |
| 51 | mmlu_pro | MMLU-Pro: More Robust Multi-Task Language Understanding | NeurIPS D&B (Spotlight) | 2024 | https://openreview.net/forum?id=y10DM6R2r3 | Robustified MMLU; difficulty-tier methodology | [priority] |
| 52 | agentbench | AgentBench: Evaluating LLMs as Agents | ICLR | 2024 | https://openreview.net/forum?id=zAdUB0aCTQ | 8-environment agent bench; multi-task framework | [priority] |
| 53 | agentboard | AgentBoard: Analytical Eval Board of Multi-Turn LLM Agents | NeurIPS D&B | 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/file/877b40688e330a0e2a3fc24084208dfa-Paper-Datasets_and_Benchmarks_Track.pdf | Multi-turn agent eval w/ analytics | [priority] |
| 54 | webarena_verified | WebArena Verified: Reliable Web-Agent Eval | OpenReview | 2025 | https://openreview.net/forum?id=94tlGxmqkN | Eval-integrity audit; 812-task re-validation | [priority] |
| 55 | rigorous_agent_bench | Establishing Best Practices for Rigorous Agentic Benchmarks | OpenReview | 2025 | https://openreview.net/pdf?id=E58HNCqoaA | Methodology paper for benchmark rigor | [priority] |
| 56 | gpqa | GPQA: A Graduate-Level Google-Proof Q&A Benchmark | COLM | 2024 | https://openreview.net/pdf?id=Ti67584b98 | Expert-curated 448 MCQs; quality-over-scale template | [priority] |

## G. Math / reasoning benchmarks (~5)
| # | slug | title | venue | year | url | why | tag |
|---|------|-------|-------|------|-----|-----|-----|
| 57 | mathvista | MathVista: Math Reasoning in Visual Contexts | ICLR (Oral) | 2024 | https://arxiv.org/abs/2310.02255 | 6,141 math+vis problems; multimodal-math template | [priority] |
| 58 | olympiadbench | OlympiadBench: Olympiad-Level Bilingual Multimodal Sci | ACL | 2024 | https://openreview.net/forum?id=OOCRYJIAMS7 | 8,476 olympiad math/physics; expert-annotated | [stretch] |
| 59 | usamo_proof | Proof or Bluff? Evaluating LLMs on 2025 USA Math Olympiad | OpenReview | 2025 | https://openreview.net/forum?id=3v650rMO5U | Proof-eval beyond final-answer; rigor template | [priority] |
| 60 | bbeh | BIG-Bench Extra Hard | arXiv | 2025 | https://arxiv.org/abs/2502.19187 | Refresh of BBH; difficulty-curation methodology | [priority] |
| 61 | hardmath | HARDMath: Challenging Applied Math Benchmark | ICLR | 2025 | https://arxiv.org/abs/2410.09988 | Applied math + analytical approx eval | [stretch] |

## Notes
- Total rows: 61 (one buffer over the requested 60). Drop any single `[stretch]` row to hit 60 exactly.
- 11 `[have]` rows match the user-listed coverage (text2cad, cad_coder, cad_recode, cadrille, cadevolve, cadcodeverify, infinity_chat, mmsi_bench, autocodebench, sportr, sportu).
- Could not verify with full confidence:
  - `cadevolve` arxiv id (placeholder pending the user's note);
  - `infinity_chat`, `mmsi_bench`, `sportr`, `sportu`, `autocodebench` OpenReview forum IDs — venues confirmed by user but exact URLs may need patching from PDFs in `paper/references/notes/`.
  - `histcad` (arXiv 2026) — title and number 2602.19171 surfaced via search; double-check before citing.
  - NeurIPS 2025 D&B `care_pd`, `mindjourney`, `omnibench` (Mexico City) — venue confirmed via NeurIPS virtual pages; OpenReview links not surfaced.
- Considered but excluded as method-papers (not benchmarks): CAD-Llama, CAD-MLLM, CadVLM, BlenderLLM (kept the paired CADBench instead), Img2CAD, GuideCAD.
- Considered but excluded as too old (pre-2024 venue): SketchGraphs, DeepCAD, Fusion360 Gallery, ABC dataset, original SWE-bench, original MMMU, original MMLU.
- Duplicates merged: CADPrompt and CADCodeVerify treated as the same `[have]` entry (single row).
- Several `[stretch]` rows are placeholders for the long tail (Spider 2.0, MEGA-Bench, etc., were promoted to `[priority]` because they are stronger structural templates).
