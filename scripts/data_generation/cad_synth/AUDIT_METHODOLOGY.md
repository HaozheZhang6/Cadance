# Family Visual Audit & Standards-Conformance Workflow

Repeatable process for catching geometry that *passes preflight* (builds OK,
non-zero volume) but doesn't actually look like the standard part it claims to
be. Used to fix `sprocket` (root-disc-with-bumps → real ISO 606 toothed
profile) and to add `double_simplex_sprocket` per DIN 8187.

Run this against every family that has a real-world standard reference —
especially the "looks plausible in bbox numbers" cases that survive automated
checks.

## When to audit

- After registering a new family.
- When a sample looks weird in Synth Monitor.
- Before any large batch run — sample 1–2 renders per family.
- When user flags specific sample IDs ("X looks wrong").

## Steps

### 1. Identify problematic samples

If user flagged specific IDs: `pd.read_csv(...).query("stem in [...]")` to pull
their params + render path.
If proactive: pull 3 random PNGs per (family × difficulty) from `views/<stem>/`.

### 2. Read the family code (cold)

Open `families/<name>.py`. Note exactly:
- What primitive ops construct the part (cylinder + cuts? polyline + extrude?
  loft? sweep?).
- Which dimensions come from a standards table vs `rng.uniform`.
- What the docstring claims vs what `make_program` actually does.

### 3. Render fresh samples

Always re-render after any code change — don't trust stale `views/`.
Use the project's preflight pattern:

```bash
export PATH="$HOME/.local/bin:$PATH" && LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 -c "
import numpy as np, cadquery as cq
from scripts.data_generation.cad_synth.pipeline.registry import get_family
from scripts.data_generation.cad_synth.pipeline.builder import build_from_program
fam = get_family('FAMILY_NAME')
opts = {'showAxes': False, 'width': 500, 'height': 500, 'projectionDir': (1.5, 1.0, 1.0)}
for diff in ['easy','medium','hard']:
    rng = np.random.default_rng(42)
    p = fam.sample_params(diff, rng)
    prog = fam.make_program(p)
    wp = build_from_program(prog)
    svg = cq.exporters.getSVG(wp.val(), opts)
    open(f'/tmp/audit_{diff}.svg','w').write(svg)
"
# Convert to PNG so the Read tool can show them
for f in /tmp/audit_*.svg; do rsvg-convert "$f" -o "${f%.svg}.png"; done
```

Then `Read /tmp/audit_<diff>.png` directly — Claude Code shows PNGs inline.

### 4. Fetch the standard (delegate to subagent)

Spawn an `Explore` or `general-purpose` subagent so the standard text doesn't
fill the main context. Brief it concretely:

> Look up <STANDARD-NUMBER> for <PART-NAME>. I need: (a) defining geometric
> formulas (with variable names + units), (b) the Table-N dimension values for
> the most common sizes, (c) a description or sketch of the tooth/feature
> profile so I can compare against a render. Report under 300 words. Cite the
> document section/page.

### 5. Diff render vs. standard

Side-by-side. Look for:
- **Topology**: is the right *kind* of feature there? (teeth vs bumps,
  through-hole vs blind, helical vs straight)
- **Proportions**: tooth height/width ratio, hub-to-bore ratio, etc.
- **Counts**: # teeth, # holes, # ribs match the param value?
- **Boundary smoothness**: sharp where it should be smooth (no chamfers)?
  smooth where it should be sharp (over-rounded)?

If the render looks fine numerically but "wrong" visually, the geometry is
wrong — trust the eye.

### 6. Rewrite, anchored to the standard

- Replace `rng.uniform` with a standards table lookup wherever possible.
- Replace boolean-cut hacks with continuous-polyline profiles when the part
  has a closed parametric outline (sprockets, gears, cams, lobes). Polylines
  are faster, more stable, and the chamfer story is cleaner.
- If you copy a working algorithm from a manual reference file (e.g.
  `tmp/manual_family_previews/`), credit it in the docstring.
- Update the docstring with the formulas you used and a `Reference:` line.

### 7. Preflight rebuild (CLAUDE.md rule)

3–5 samples per difficulty through the actual `build_from_program` — bbox
sanity, non-zero volume, no exceptions. Then re-render and re-view step 3.

### 8. Run tests + lint

```bash
uv run pytest tests/test_data_generation/ -x -q
uv run black scripts/data_generation/cad_synth/families/<name>.py
uv run ruff check scripts/data_generation/cad_synth/families/<name>.py
```

### 9. Record the outcome

- `PROGRESS.md`: one-line entry per family fixed, naming the geometry change.
- `TASK_QUEUE.md`: mark UA-N done with date if user-assigned.
- Don't delete the old PNG renders — they're proof of the fix.

## Common geometry pitfalls (from past audits)

| Symptom in render               | Likely cause                                          |
| ------------------------------- | ----------------------------------------------------- |
| Smooth disc, no teeth visible   | "Bumps unioned to root disc" with too-small bump_r    |
| Teeth as raised cylinders       | Fundamentally wrong topology — should be cuts in tip disc OR polyline outline |
| Tooth widths inconsistent       | Disc thickness sampled `rng.uniform` instead of standard b1 table |
| Crashes on hard difficulty only | Boolean cut count scales with `z` — switch to single polyline extrude |
| No chamfers, sharp top edges    | Missing `Op("edges", {"selector": ">Z"})` + `Op("chamfer",...)` after extrude |
| Bore covered by chamfer ring    | Bore cut after chamfer when chamfer_size > tip-to-bore clearance — cut bore first OR use cutThruAll |

## Reference: the sprocket fix (2026-04-18)

Two-pass rewrite illustrates the workflow:

**Pass 1** — diagnosed "no teeth visible" in samples 1431/1553/1560/1691.
Reason: old code did `circle(root_d).extrude(t).union(small_cylinders_at_pcd)`
with bump radius `dr*random` — bumps too small to break the silhouette.
Replaced with `circle(tip_d).extrude(t)` + cut z seating cylinders. Teeth
appeared, but renders showed straight-cut tooth flanks (not the curved ISO 606
profile).

**Pass 2** — switched to continuous-polyline profile per
`tmp/manual_family_previews/manual_double_sprocket.py`: build the entire
sprocket outline as one CCW polyline (root arc + flank line + tip midpoint per
gap × z gaps), extrude in one shot, chamfer top/bottom edges before bore. No
booleans for the teeth. Same approach generalised to `double_simplex_sprocket`
with two extruded toothed discs unioned to a full-length central hub.

The helper lives in `families/base.py::iso606_sprocket_profile()` so any
future chain-related family (e.g. timing pulley) can reuse the same primitive.
