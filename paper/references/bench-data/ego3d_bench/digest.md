# ego3d_bench — Ego3D-Bench: Spatial Reasoning with Vision-Language Models in Ego-Centric Multi-View Scenes

**Venue:** arXiv 2025 (preprint) · **Year:** 2025 · **URL:** Project Page (Huawei) · **PDF:** raw.pdf · **arXiv:** 2509.06266

## TL;DR
8,600 QA over ego-centric multi-view outdoor scenes (NuScenes, Waymo,
Argoverse) probing 5 spatial categories; 16 SOTA VLMs lag human; the
authors' Ego3D-VLM (textual cognitive map) gives +12% on multi-choice QA
and +56% on absolute-distance estimation.

## Storyline (5-piece)
- **Problem.** Real embodied agents — self-driving cars, mobile robots —
  consume *ego-centric multi-view* streams (front / left / right / rear)
  with explicit spatial semantics. Existing spatial benchmarks use
  single-image or static-indoor video, missing this regime entirely; even
  All-Angle Bench uses third-person multi-view, not ego.
- **Contribution.** (i) Ego3D-Bench: 8.6K QA from validation splits of
  NuScenes, Waymo Open Dataset, and Argoverse 1; ego-centric and
  object-centric categories; human annotators central to construction and
  audit. (ii) Ego3D-VLM: post-training framework that builds a textual
  cognitive map (referring-expression comprehension + metric depth → 3D
  coords → text) plug-in for any VLM.
- **Evidence (approach).** QA carefully filtered to exclude
  single-view-answerable items and general-knowledge shortcuts. 5 spatial
  categories (relative position, distance, motion, layout, ego-motion).
  Cognitive-map prompt encodes 3D coords of referred objects in a
  shared frame, giving the VLM explicit geometric grounding.
- **Experiments.** 16 VLMs (GPT-4o, Gemini-1.5-Pro, InternVL3,
  Qwen2.5-VL, etc.) plus 3D-specialist VLMs; human upper bound included.
  Ego3D-VLM consistently lifts SOTA across backbones; large gap remains
  between best model and human.
- **Analysis.** Point-cloud and BEV alternatives are slow (10× inference
  time) and brittle to dynamic scenes; textual cognitive map is lighter
  and more general. Ablations show REC + depth + global-frame all needed;
  removing any single component drops performance significantly.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|---|---|---|---|---|
| 1 | 1 | hero composite | hero | ego multi-view sample + 5-category icons + human-vs-VLM bar | gap and benchmark scope |
| 2 | 3 | pipeline diagram | pipeline | data-creation flow + sample distribution | construction rigor |
| 3 | 4 | category panel | taxonomy | one example per spatial category | makes 5 categories concrete |
| 4 | 5 | method diagram | ablation | Ego3D-VLM = REC + depth + cognitive-map text | proposed method overview |
| 5 | 8 | results table | headline-results | 3D-VLMs and generalists on Ego3D-Bench | Ego3D-VLM lifts all backbones |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B)
- **Multi-view-with-explicit-frame** parallels CAD's 4-view (front /
  right / top / iso); cite Ego3D-Bench when motivating multi-view input
  format and for the "explicit camera label" prompting style.
- **Filter out single-view-answerable.** Critical discipline: ensure each
  BenchCAD question genuinely requires multi-view (or parametric)
  reasoning, not a single-view shortcut. We should run a single-view
  ablation and report which questions remain hard.
- **Plug-in method as add-on.** Ego3D-VLM works on any VLM. If we ship a
  baseline prompting strategy (e.g. "view-then-reason"), keep it
  backbone-agnostic to maximise reuse.
- **Aggregate-from-existing-datasets** strategy (NuScenes / Waymo /
  Argoverse) — Fusion360 + DeepCAD aggregation is methodologically aligned
  and well-precedented.
- **Avoid narrow-domain critique.** 8.6K with mostly outdoor / automotive
  scenes feels narrow; reviewers asked for diversity. BenchCAD's 106
  families across 8 industrial domains is a strength to highlight
  prominently in abstract and intro.

## One-line citation
Gholami, M., Rezaei, A., Weimin, Z., Mao, S., Zhou, S., Zhang, Y.,
Akbari, M. (2025). *Spatial Reasoning with Vision-Language Models in
Ego-Centric Multi-View Scenes (Ego3D-Bench).* arXiv 2509.06266.
