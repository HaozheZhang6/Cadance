# Evaluation Suite Design Guide

This document captures design principles, conventions, and lessons learned for creating evaluation samples in the Intent-to-CAD test suite.

---

## Directory Structure

```
evaluation_suite/
├── train/              # Training samples (visible during development)
│   ├── level_1_easy/
│   ├── level_2_medium/
│   ├── level_3_hard/
│   └── level_4_expert/
├── eval/               # Held-out evaluation samples (prevent overfitting)
│   └── (same structure)
└── manifest.json       # Split assignments and metadata
```

Each test case directory contains:
- `intent.txt` - Natural language description
- `spec.json` - Expected properties and metadata
- `ground_truth.py` - Reference CadQuery implementation

---

## Sample Creation Checklist

When creating a new evaluation sample:

1. **Write the intent first** - Clear, unambiguous natural language
2. **Implement ground_truth.py** - Working CadQuery code
3. **Generate spec.json** - Use `generate_specs.py` to extract properties from execution
4. **Verify with replay** - Run replay to ensure IoU ≈ 1.0 when LLM generates correct code
5. **Assign to train/eval split** - 60% train, 40% eval typical

---

## Workplane Convention

**Default: Always use XY workplane** unless the intent explicitly specifies otherwise.

### Why XY?

1. **CadQuery default** - `Workplane("XY")` is the natural starting point
2. **LLM behavior** - Models naturally generate XY-based code
3. **IoU fairness** - Avoids false failures from orientation mismatches
4. **Consistency** - Reduces arbitrary variation between samples

### When to use XZ or YZ

Only use non-XY workplanes when:
- Intent explicitly specifies orientation (e.g., "vertical profile in the XZ plane")
- Functional requirement demands it (e.g., "must mate with existing part at this orientation")
- The shape semantically requires it (rare)

### Historical Issue (2026-01-26)

Several ground truths were written with XZ workplane "for clarity" without specification in the intent:

| Test | Original | Issue |
|------|----------|-------|
| L1_05 | XZ | L-shape extruded in Y, but LLM uses XY → IoU=0.0 |
| L2_06 | XZ | Revolved cup, XZ arbitrary → IoU=0.03 |
| L3_04 | XZ | L-bracket, no orientation specified → IoU=0.0 |
| L4_02 | XZ | Pipe elbow, orientation arbitrary → IoU failed |

**Correlation**: 80% fail rate for XZ samples vs 13% for XY samples.

**Fix**: Updated all to use XY workplane, improving true success rate.

---

## Intent Writing Guidelines

### Be Specific About Dimensions

Good:
```
Create a rectangular box 100mm wide, 50mm deep, and 30mm tall.
```

Bad:
```
Create a box with dimensions 100x50x30.
```
(Ambiguous which dimension is which)

### Avoid Implicit Orientation

Good:
```
Create an L-shaped profile in the XY plane and extrude it 40mm in the Z direction.
```

Acceptable (uses XY default):
```
Create an L-shaped profile and extrude it 40mm.
```

Bad (introduces unnecessary constraint):
```
Create an L-shaped profile and extrude it 40mm. Use the XZ plane.
```
(Why XZ? If there's no reason, don't specify it.)

### Specify Functional Requirements, Not Implementation

Good:
```
Create a cup with outer diameter 60mm, inner diameter 52mm, height 70mm.
```

Bad:
```
Create a cup by revolving a rectangle around the Y axis.
```
(Over-specifies implementation; there are multiple valid ways)

### Use Clear Terminology

- "diameter" vs "radius" - be explicit
- "width/depth/height" or "X/Y/Z" - pick one convention
- "fillet" vs "chamfer" - don't assume knowledge
- "through hole" vs "blind hole" - specify depth

---

## Spec Generation

Always use the `generate_specs.py` script to create `spec.json`:

```bash
uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_specs.py
```

This ensures:
- Volume is computed from actual geometry (not calculated by hand)
- Face/edge counts match BREP representation (not mathematical ideals)
- Bounding box is accurate

### Manual spec creation pitfalls

| Property | Manual Error | Reality |
|----------|--------------|---------|
| Cylinder edges | 2 (top + bottom) | 3 (includes seam edge) |
| Sphere edges | 0 | 1 (pole singularity) |
| Filleted box faces | 6 + fillet faces | Depends on implementation |

---

## Complexity Levels

### Level 1: Easy (Single Primitive)
- One CadQuery operation
- No boolean operations
- Examples: box, cylinder, sphere, simple extrusion

### Level 2: Medium (2-3 Operations)
- Simple combinations
- One boolean operation (union/subtract)
- Basic modifiers (fillet, chamfer)
- Examples: box with hole, chamfered cylinder

### Level 3: Hard (4-6 Operations)
- Multiple boolean operations
- Complex sketches (polylines, arcs)
- Patterns (linear, circular)
- Examples: flanged cylinder, bracket with holes

### Level 4: Expert (7+ Operations)
- Complex assemblies
- Sweeps, lofts
- Multiple coordinate systems
- Examples: pipe elbow, bearing housing

---

## Ground Truth Code Style

```python
"""Ground truth CadQuery code for {TEST_ID}: {NAME}.

Brief description of what this creates.

Design decisions:
- Why certain approaches were chosen
- Any non-obvious implementation details
"""

import cadquery as cq

# Clear comments explaining each step
result = (
    cq.Workplane("XY")  # Always start with XY unless specified
    .box(100, 50, 30)
    # ... operations ...
)

# Expected properties (for reference, actual values from generate_specs.py):
# - Volume: X mm³
# - Faces: N
# - Edges: M
```

---

## IoU Considerations

### What IoU Catches

- Position errors (shape at wrong location)
- Orientation errors (rotated incorrectly)
- Scale errors (wrong size)
- Shape errors (fundamentally different geometry)

### What IoU Doesn't Catch

- Symmetric rotations (cube rotated 90° = IoU 1.0)
- Internal structure (if exterior matches)

### Threshold

Default 90% IoU threshold. Tests should achieve:
- IoU ≈ 1.0 for correct implementations
- IoU < 0.5 for significantly wrong shapes
- IoU = 0.0 for position/orientation mismatches

If a correct implementation achieves < 90% IoU, investigate:
1. Is the ground truth using non-XY workplane unnecessarily?
2. Is there a position offset in the ground truth?
3. Does the intent have ambiguous orientation?

---

## Adding New Samples

1. **Identify gap** - What skill/primitive is undertested?
2. **Write intent** - Follow guidelines above
3. **Implement ground truth** - Use XY workplane, clear code
4. **Generate spec** - Run generate_specs.py
5. **Test locally** - Run single test to verify
6. **Check IoU** - Ensure correct implementation gets IoU ≈ 1.0
7. **Assign split** - Add to train/ or eval/ directory
8. **Update manifest** - If needed

---

## Troubleshooting

### "IoU = 0 but properties match"

Likely cause: Workplane mismatch (XZ vs XY)
Fix: Standardize ground truth to XY

### "Face/edge count mismatch"

Likely cause: BREP representation differs from mathematical expectation
Fix: Regenerate spec.json from actual execution

### "Volume slightly off"

Likely cause: Floating point precision or different construction approach
Fix: Check tolerance (1% default), may need to adjust spec

### "LLM generates different but equivalent code"

This is expected! The evaluation checks geometric output, not code.
If IoU ≈ 1.0, the test should pass regardless of implementation approach.

---

## Ensuring Solid Output

Ground truth code must produce a valid Solid when `.val()` is called. This is critical for IoU computation, which requires volumes from both generated and ground truth geometry.

### Issue: Workplane Context After Operations

CadQuery operations like `shell()`, `fillet()`, and `chamfer()` with face selectors leave the workplane context pointing to the selected faces, not the resulting solid. Similarly, `revolve()`, `loft()`, and `sweep()` may leave context in unexpected states.

When `.val()` is called on such a workplane, it returns the wrong object (Face, Shell, Compound, or None) with 0 or invalid volume.

### Historical Issue (2026-01-27)

| Test | Operation | Error | Fix |
|------|-----------|-------|-----|
| L2_05 | `.faces(">Z").shell(-3)` | `Null TopoDS_Shape` | Added `.end()` |
| L2_13 | `.revolve()` in XZ plane | `gt volume = 0` | Changed to XY plane |
| L2_15 | `.faces(">Z or <Z").shell(-5)` | `Null TopoDS_Shape` | Added `.end()` |
| L3_11 | `.close().revolve()` in XZ plane | `gt volume = 0` | Changed to XY plane |

### Best Practices

1. **After shell operations**, use `.solids()` to extract the Solid from the Compound:
   ```python
   # BAD - shell returns Compound, .val() gives wrong object
   result = cq.Workplane("XY").box(80, 60, 50).faces(">Z").shell(-3)

   # GOOD - extract solid from compound
   result = cq.Workplane("XY").box(80, 60, 50).faces(">Z").shell(-3).solids()
   ```

2. **For revolve**, use `rect(centered=False)` or `polyline` with default revolve:
   ```python
   # GOOD - rect with centered=False for simple profiles
   result = cq.Workplane("XZ").rect(30, 5, centered=False).revolve()

   # GOOD - polyline for complex profiles (offset from axis)
   result = (
       cq.Workplane("XZ")
       .moveTo(10, 0)  # Start offset from axis
       .polyline([(25, 0), (25, 8), (18, 8)])
       .close()
       .revolve()
   )

   # BAD - lineTo approach often produces invalid geometry
   result = cq.Workplane("XZ").moveTo(0, 0).lineTo(30, 0).lineTo(30, 5).close().revolve()
   ```

3. **Validate ground truth produces a solid**:
   ```python
   assert result.val() is not None, "Ground truth produced None"
   assert hasattr(result.val(), "Volume"), "Result is not a Solid"
   assert result.val().Volume() > 0, "Volume must be positive"
   ```

4. **Run generate_specs.py** after any ground truth changes to update spec.json with actual geometry properties.
