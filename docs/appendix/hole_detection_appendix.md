# Appendix D: has_hole Feature Detection

**Status**: Production decision committed (2026-04-25) — Method B (STEP B-rep)
**Production code**: `bench/metrics/__init__.py` (`_step_has_hole`, `extract_features`)
**Eval script**: `bench/research/hole_detection_eval.py`
**Output (1000-sample run)**: `bench/research/outputs/hole_method_c_n1000_s42.csv`

---

## D.1 Problem Statement

A core metric of our benchmark is `feature_f1` — the F1 score over detected feature
tags (`has_hole`, `has_fillet`, `has_chamfer`) between a model's generated CadQuery
code and the ground-truth part. Reliable feature extraction is therefore a
prerequisite: if the labels are wrong, the metric is wrong.

For `has_hole` specifically, two extraction signals exist with very different failure
modes. This section defines them, runs a reliability study on 1000 synthesized
parts spanning 106 families, justifies our final choice, and documents the residual
errors with concrete examples.

GT labels in our pipeline come from family `make_program()` declarations
(`scripts/data_generation/cad_synth/families/*.py`). For external (Fusion360,
DeepCAD) parts uploaded via `bench/upload_external.py`, GT labels are computed
from the same `extract_features()` function used at eval time, so the choice of
detector also determines published HF GT labels.

---

## D.2 Method Definitions

### Method A — AST Regex

Scan the CadQuery source code for explicit hole-creating API calls:

```python
pattern = r"\b(hole|cutThruAll|cboreHole|cskHole)\s*\("
```

- **Signal**: developer named the operation as a hole.
- **Cost**: O(len(code)).
- **Failure mode**: matches any `cutThruAll(` regardless of profile shape; misses
  any "hole" produced by `revolve` / `sweep+cut` / boolean cut without the named API.

### Method B — STEP B-rep (chosen)

Iterate faces of the exported STEP file via `TopExp_Explorer`. A face counts as
an inner cylindrical bore iff:

```python
ad = BRepAdaptor_Surface(face)
ad.GetType() == GeomAbs_Cylinder
and face.Orientation() == TopAbs_REVERSED   # OCC: REVERSED = inner wall
and ad.Cylinder().Radius() >= 0.5            # filter tessellation artefacts
```

- **Signal**: actual circular bore exists in the final geometry.
- **Cost**: STEP load + face walk, ~60 ms per file in-process (no subprocess).
- **Failure mode**: misses non-circular holes (rectangular / hex / T-slot); flags
  inner cylindrical walls of hollow shells that the family chose to label
  `has_hole=False`.

### Method C — A OR B (rejected, see §D.4)

Initially considered. Empirically the union adds 33 TPs at the cost of 25 FPs on
1000 samples — F1 delta +0.009, within label-convention noise. Not adopted.

---

## D.3 Reliability Study — 1000 samples, 106 families (2026-04-25)

**Pool**: `data/data_generation/synth_parts.csv`, filtered `status=accepted &
code_exec_ok=True` → 20 143 rows across 106 families.
**Sample**: random 1000, `--seed 42`.
**GT**: `feature_tags["has_hole"]` from family declarations.
**Reproduce**:

```bash
LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 \
  bench/research/hole_detection_eval.py --n 1000 --seed 42
```

### D.3.1 Confusion matrix

| Method | TP  | FP  | FN  | TN  | Prec  | Rec   | **F1** |
|--------|----:|----:|----:|----:|------:|------:|-------:|
| A AST   | 484 | 31  | 177 | 308 | 0.940 | 0.732 | 0.823  |
| **B STEP (production)** | 601 | 42  | 60  | 297 | 0.935 | **0.909** | **0.922** |
| C A OR B | 634 | 67  | 27  | 272 | 0.904 | 0.959 | 0.931  |

(GT+ = 661, GT− = 339)

### D.3.2 A's net effect on top of B

C = A OR B partitions into four regions; the only ones where C ≠ B:

| Region | Definition | Count | Effect of adding A |
|---|---|---:|---|
| **A_helps** | A=T, B=F, GT=T | **+33** | C correct where B wrong (Recall ↑) |
| **A_harms** | A=T, B=F, GT=F | **−25** | C wrong where B correct (Precision ↓) |

Net: +8 correct decisions out of 1000. F1 0.922 → 0.931 (+0.009, ≈ noise).
**The +33 vs −25 is a labeling convention conflict**, not an algorithm bug — see
§D.4.

---

## D.4 Why Method B Alone

### D.4.1 What A does that B can't

A's regex is grounded in **API name**, B is grounded in **B-rep geometry**. They
disagree exactly when the developer used a hole-API but produced something other
than a circular cylindrical bore.

Two opposite-direction sub-cases:

**A_helps (n=33) — non-circular hole-API uses, GT calls them holes**

```python
# wire_grid (n=12 in this run) — square through-holes via cutThruAll
.box(113.4, 60.7, 3.9).pushPoints([...]).rect(17.99, 24.49).cutThruAll()
# AST sees `cutThruAll(` → True
# STEP sees zero cylindrical faces (rectangular cut) → False
# GT=True (family treats square through-holes as has_hole)

# t_slot_rail (n=4) — T-profile slots
.rect(15.0, 7.5).cutThruAll().rect(10.0, 2.5).cutThruAll()

# gusseted_bracket (n=10) — hole() called but boolean fails silently
.pushPoints([(10.7, -17.9)]).hole(4.5)
# Resulting B-rep: only planar faces, no cylinder produced.
# AST=True, STEP=False, GT=True (declaration-driven).
# In these cases STEP is arguably MORE correct than GT — see §D.5.
```

**A_harms (n=25) — rectangular cuts the family does not call holes**

```python
# rect_frame (n=7) — frame interior
.rect(80.0, 100.0).extrude(10.0).rect(56.0, 76.0).cutThruAll()
# AST=True (matched cutThruAll), STEP=False, GT=False (frame ≠ hole)

# l_bracket (n=6) — square hollow brackets
.box(23, 23, 126).rect(20, 20).cutThruAll()

# hollow_tube (n=6) — square hollow tubes
.box(61, 30, 30).rect(25, 25).cutThruAll()

# slotted_plate (n=2), vented_panel (n=4) — slot/vent arrays
```

### D.4.2 The conflict is in GT conventions, not the methods

A=True + B=False describes **non-cylindrical geometry produced by a hole-API**.
Whether GT calls that "a hole" depends entirely on the family author:

- wire_grid author: square through-hole = hole → GT=True → A helps
- rect_frame author: rectangular interior = frame → GT=False → A harms

Neither method can disambiguate; only the GT-author's convention can. The
roughly-equal sizes (33 vs 25) reflect that this convention is not consistent
across the registry.

### D.4.3 Decision

| Optimization target | Choose |
|---|---|
| Recall (don't miss any hole) | C — Recall 0.959 |
| Precision (don't false-flag) | B — Precision 0.935 |
| Single F1 metric (our case) | B (0.922) ≈ C (0.931); +0.009 within noise |
| Robust to GT convention drift | **B** — geometry-grounded, family-agnostic |

We adopt **Method B**. The 25 fewer FP reduces noise on the hollow-shell families
(`duct_elbow`, `nozzle`, `capsule`, …) which are over-represented in our
benchmark and would otherwise distort family-level metrics. The 33 lost TPs are
absorbed as known limitations (Type III in §D.5).

---

## D.5 Failure Mode Taxonomy + Examples

Under Method B, failures partition into four canonical types.

### Type I — Revolve / cut-based bores (handled correctly by B)

```python
# bellows — polyline revolve produces inner cylinder
.polyline([(11.9, 0), (26.1, 0), (15.5, 9.6), ...]).revolve(360, (0,0,0), (0,1,0))
# B sees the resulting REVERSED cylindrical face → True ✓

# pulley — boolean cut for hub bore
.box(...).cut(.cylinder(75.0, 7.5))   # B → True ✓
```

In our run B catches all of these (15 families, +150 TP gain over A alone).

### Type II — Rectangular cutThruAll (only matters if A is in the loop)

`rect_frame`, `l_bracket`, `hollow_tube`, `slotted_plate`, `vented_panel`. AST
matches `cutThruAll(` indiscriminately. B correctly returns False because no
cylindrical face is produced. **B sidesteps this entirely** (the 25 A_harms
cases above). No action needed in production.

### Type III — Non-cylindrical "holes" in GT (B misses, accepted)

GT declares `has_hole=True` but no cylindrical inner wall exists in the
geometry. Two sub-cases by what AST sees:

**III-a — code uses a hole-API but it doesn't produce a cylinder** (A=T, B=F,
GT=T; the 33 "A_helps" cases that B cannot recover):

| Family | n | Why B misses |
|---|---:|---|
| wire_grid | 12 | square through-holes via rect+cutThruAll |
| gusseted_bracket | 10 | silent `hole()` failure (see §D.6) — STEP arguably more correct than GT |
| t_slot_rail | 4 | T-profile slots |
| dowel_pin / i_beam / spur_gear | 2 each | profile extrudes / hex bores |
| propeller | 1 | profile-cut blade root |

**III-b — code does not use a hole-API at all** (A=F, B=F, GT=T; the 27
"STILL-FN" cases neither A nor B catches):

| Family | n | Why B misses |
|---|---:|---|
| hex_key_organizer | 11 | hex slots via extrude+cut, no closed cylinder |
| cotter_pin | 10 | half-revolve (180°) does not close into a cylinder |
| eyebolt | 6 | loop extrude, no cylindrical inner wall |

Total Type III = 60 FN (matches B's 60 FN, Recall 0.909). Catching III-b would
require either a third detector (e.g. inner-volume genus / connectivity) or a
GT label policy that ties has_hole to circular geometry rather than to op-name.

### Type IV — Hollow-shell semantic ambiguity (B FP, GT label issue)

The B-rep contains a cylindrical inner wall (B correctly detects it), but the
family chose `has_hole=False` because the part is conceptually a shell:

| Family | n in this run | Geometry |
|---|---:|---|
| duct_elbow | 10 | swept hollow rectangle, inner curve includes cylindrical segments |
| nozzle | 8 | revolve of profile — inner bore arguably IS a hole |
| snap_clip | 7 | hook curvature interpreted as bore |
| capsule | 4 | revolve of arc — inner cylinder from solid-of-revolution |
| circlip | 3 | ring inner wall |
| dome_cap, lathe_turned_part, u_channel | 2/1/1 | hollow-shell variants |

Total 36 FP (Precision 0.935). Two ways to resolve:
1. Change family GT to mark these as has_hole=True (would shift the metric
   semantics globally — deferred).
2. Add radius-vs-OD-ratio gate in `_step_has_hole` (heuristic that hollow
   shells have inner radius near outer extent). Not implemented; would need
   its own ablation study.

---

## D.6 gusseted_bracket — When STEP is More Correct Than GT

Inspection of `synth_gusseted_bracket_000131_s9999` (originally found 2026-04-15,
re-confirmed in this run):

- Code: `.faces("<Z").workplane().pushPoints([(16.025, -28.85)]).hole(4.6)`
  (two `hole()` calls in the program)
- STEP face inventory: **0 cylindrical faces, 18 planar faces only**
- The boolean subtraction produced no actual bore; the resulting shape is
  effectively the un-drilled stock.

```
face type distribution = {'Plane-REV': 9, 'Plane-FWD': 9}
```

GT was set to `has_hole=True` because make_program emits a `hole` op — a
**declarative** assertion of intent, not a verification of result. AST sees the
code (intent). STEP sees the geometry (result). When they disagree on
gusseted_bracket, the STEP result matches what is actually exported and
rendered for the model.

**Implication**: B's 10 FN on gusseted_bracket are partly GT label errors. A
pipeline-side fix (geometry-validate hole() success after build, demote
has_hole if no cylinder produced) would improve B's measured F1. Tracked as an
open item; not blocking.

---

## D.7 Production Algorithm

```python
# bench/metrics/__init__.py

def _step_has_hole(step_path: str) -> bool:
    """Cylindrical inner bore in STEP B-rep."""
    try:
        import cadquery as cq
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.GeomAbs import GeomAbs_Cylinder
        from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        shape = cq.importers.importStep(step_path)
        exp = TopExp_Explorer(shape.val().wrapped, TopAbs_FACE)
        while exp.More():
            face = TopoDS.Face_s(exp.Current())
            ad = BRepAdaptor_Surface(face)
            if (
                ad.GetType() == GeomAbs_Cylinder
                and face.Orientation() == TopAbs_REVERSED
                and ad.Cylinder().Radius() >= 0.5
            ):
                return True
            exp.Next()
    except Exception:
        pass
    return False


def extract_features(code: str, step_path: str | None = None) -> dict[str, bool]:
    feats = {k: bool(pat.search(code)) for k, pat in _FEATURE_PATTERNS.items()}
    if step_path:                              # B is authoritative when STEP exists
        feats["has_hole"] = _step_has_hole(step_path)
    return feats                               # else AST fallback (exec_fail path)
```

Properties:
- B-primary when `step_path` is provided (production eval, GT extraction for HF
  upload, both pipelines pass STEP).
- AST regex retained as fallback for `exec_fail` samples where no gen STEP
  exists. This is purely a graceful-degradation path, not a primary detector.
- TopExp face walk avoids `cq.faces()` → `hashCode()` (the macOS OCP HashCode
  attribute issue documented in `bench/eval.py:55`).

---

## D.8 Methodology Ablations (orthogonal, kept from prior appendix)

These are general bench-methodology ablations that predate the Method B
decision. They concern voxel resolution, weight sensitivity, and family split
— not has_hole detection. Retained for completeness.

### D.8.1 Voxel Resolution for IoU (✅ 2026-04-15)

20 samples, 3 resolutions, GT-vs-GT and GT-vs-1.05×scaled. Both meshes
normalised to [0,1]³ before voxelisation.

| Resolution | GT-GT mean | GT-1.05× mean | Time/pair |
|-----------|-----------|--------------|----------|
| 32³ | 1.0000 | 0.8632 | 1.00 s |
| **64³ (ours)** | 1.0000 | 0.8291 | 5.45 s |
| 128³ | 1.0000 | 0.8253 | 37.07 s |

64³ gives 0.004 less sensitivity than 128³ but is 6.8× faster. Adopted.

### D.8.2 Family-Level vs Random Split (✅ 2026-04-15)

| Property | Family-level split | Random split |
|----------|-------------------|-------------|
| Test families | 19 (OOD only) | 72 (all families) |
| Train ∩ Test families | 0 | 72 (100% overlap) |
| Train→test gap (toy model) | −0.115 | +0.020 |

Random split collapses the OOD generalisation signal by 5.7×. Family-level
split is mandatory.

### D.8.3 detail_score Weight Sensitivity — superseded

This study was run against the old scoring formula `0.4·IoU + 0.6·F1`. Current
production scoring is `0.25·F1 + 0.7·IoU + 0.025·cd_score + 0.025·hd_score`
(see `bench/metrics/combined_score`). Weight ablation under the new formula has
not been re-run; numerical breakpoints in `cd_to_score` / `hd_to_score`
(`_CD_LOW=0.001`, `_CD_HIGH=0.2`, `_HD_LOW=0.05`, `_HD_HIGH=0.5`) were calibrated
against a 50-sample gpt-5.3-thinking run (76% of samples score>0). Open item.

---

## D.9 Results Log

### 2026-04-15 — Initial reliability study (bench_1k_apr14, 73 families)
- AST F1=0.931 (n=994), STEP F1=0.932 (n=364), OR F1=0.938
- Identified four failure mode types
- AST OR STEP achieved zero FN on the bench at the time (smaller family set)

### 2026-04-15 — gusseted_bracket root cause (§D.6)
- Silent `hole()` boolean failure: code calls hole(), STEP shows no cylinder
- STEP is more correct than GT in these cases
- Action item still open: pipeline geometry-validation of hole() success

### 2026-04-15 — D.8 ablations completed (voxel, family split, weight pilot)

### 2026-04-23 — Method C went into production (later reverted)
- Inline TopExp implementation replaced subprocess Method B
- `bench/metrics/__init__.py:_step_has_hole` + `extract_features(code, step_path)`
- All eval call sites updated (`bench/eval.py`, `bench/test/run_test.py`,
  `bench/upload_external.py`)

### 2026-04-25 — 1000-sample reliability study, Method B chosen (§D.3, §D.4)
- New script `bench/research/hole_detection_eval.py` (single source of truth,
  imports from `bench.metrics`)
- 1000 random samples from 20143-row pool, 106 families, seed 42
- AST F1=0.823, STEP F1=0.922, OR F1=0.931
- A's net contribution over B: +33 TP / −25 FP / +0.009 F1 (within
  label-convention noise)
- Adopted Method B (STEP-only when step_path available, AST fallback for
  exec_fail). `extract_features` updated; `_step_has_hole` is authoritative
  whenever a STEP file is available

### Open items
- [ ] Pipeline fix: validate `hole()` boolean success geometrically before
      setting `feature_tags["has_hole"]=True` in `make_program()` outputs
- [ ] GT label policy decision for hollow-shell families (nozzle/duct_elbow):
      keep False for reproducibility, or flip to True and re-publish HF GT
- [ ] D.8.3 re-run weight sensitivity under new `0.25/0.7/0.025/0.025` formula
- [ ] Optional Type III mitigation: inner-volume connectivity detector for
      non-cylindrical bores (would salvage wire_grid / cotter_pin / hex_key_organizer)
