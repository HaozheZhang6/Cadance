---
license: cc-by-4.0
task_categories:
- image-to-3d
- text-generation
tags:
- cad
- cadquery
- synthetic
- benchmark
size_categories:
- 1K<n<10K
---

# CAD Synthesis Benchmark — test_bench

Small-scale benchmark for **image → CadQuery code** generation.

**Task**: Given rendered views of an industrial part, generate CadQuery code that reproduces it.

**Evaluation**: Execute code → export STEP → compute IoU vs GT STEP.

## Splits

| Split | Families | Description |
|-------|----------|-------------|
| `test-iid` | 54 train families, XY plane | In-distribution test |
| `test-ood-family` | 19 held-out families | Family generalization |
| `test-ood-plane` | 54 train families, XZ/YZ | View generalization |

OOD families: `bellows`, `worm_screw`, `torus_link`, `impeller`, `propeller`,
`chair`, `table`, `snap_clip`, `waffle_plate`, `wire_grid`, `mesh_panel`,
`t_pipe_fitting`, `pipe_elbow`, `duct_elbow`, `dome_cap`, `capsule`,
`coil_spring`, `bucket`, `nozzle`

## Sample Fields (bench_manifest.jsonl)

```json
{
  "stem": "synth_handwheel_000042_s9999",
  "family": "handwheel",
  "difficulty": "easy",
  "base_plane": "XY",
  "split": "test-iid",
  "feature_tags": {"has_hole": true, "has_fillet": false, "has_chamfer": false},
  "feature_count": 1,
  "ops_used": ["circle", "extrude", "union", "cut"],
  "gt_code_path": "data/test-iid/synth_handwheel_000042_s9999/code.py",
  "gt_step_path": "data/test-iid/synth_handwheel_000042_s9999/gen.step",
  "composite_png": "data/test-iid/synth_handwheel_000042_s9999/views/composite.png"
}
```

## Metrics

- `exec_ok`: code executes (0/1)
- `iou`: voxel IoU vs GT STEP
- `feature_f1`: F1 of feature_tags (hole/fillet/chamfer/slot)
- `detail_score`: `0.4 × iou + 0.6 × feature_f1` (primary ranking metric)

## Generation

- Pipeline: `cad_synth` (73 families, parametric, multi-plane)
- Seed: 9999 (held out from training seed 1337)
- Rendered: 4-view normalized PNGs + 2×2 composite
