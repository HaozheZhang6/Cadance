# DFM Verification Demo Parts

This directory contains ops program test cases demonstrating the **intent-verification-refinement loop** for mechanical design.

## Demo Suite Overview

| Level | Parts | Purpose |
|-------|-------|---------|
| **L1** | 3 | Simple primitives (block, cylinder, plate) - baseline passing cases |
| **L2** | 7 | Medium complexity with intentional violations |
| **L3** | 4 | Multi-feature assemblies (valve body, enclosure, gear housing) |
| **L4** | 6 | Industrial parts with multiple interacting DFM constraints |
| **L5** | 2 | Expert-level complex geometries |

## DFM Rules Verified

The verification pipeline checks:

1. **Minimum Hole Diameter** (ERROR if < 0.5mm)
   - Small holes require micro-machining/EDM
   - Standard tooling limit ~0.5mm

2. **Hole L/D Ratio** (WARN if > 10)
   - Deep holes require gun drilling or pecking
   - Recommended max L/D = 4, typical = 10, feasible = 40

3. **Minimum Fillet Radius** (WARN if < 0.2mm)
   - Internal corners need tool clearance
   - Recommended radius = 1/3 × cavity depth

4. **Minimum Wall Thickness** (WARN if < 1.0mm)
   - Thin walls reduce stiffness, cause chatter
   - Metal: min 0.8mm, Plastic: min 1.5mm

## Iterative Refinement Pattern

The L4/L5 parts demonstrate the refinement loop:

```
v1 (Original Design)     →     Verification     →     v2 (Revised Design)
   with DFM issues              detects issues          fixes applied
```

### Example: Hydraulic Manifold

**v1 Issues:**
- 0.3mm orifice (ERROR: too small)
- L/D=15 channels (WARN: too deep)
- 0.6mm walls (WARN: too thin)

**v2 Fixes:**
- 0.8mm hole + external restrictor fitting
- Split channels into L/D=8 sections with plugs
- Increased spacing for 2.0mm walls

## Running Demos

```bash
cd cadance_vlad
source .venv/bin/activate
python tests/dfm_test_cases/demos/run_all_demos.py
```

Results are saved to `results/demo_results_summary.json`

## Part Catalog

### L1: Simple Parts (All PASS)
- `L1_cylinder_ops.json` - Basic turned cylinder
- `L1_plate_holes_ops.json` - Flat plate with mounting holes
- `L1_simple_block_ops.json` - Rectangular block

### L2: Medium Complexity
- `L2_bearing_housing_ops.json` - Pillow block bearing mount
- `L2_heat_sink_ops.json` - Finned heat sink
- `L2_l_bracket_ops.json` - Simple L-bracket
- `L2_sharp_corner_violation_ops.json` - Pocket with 0.1mm corners (WARN)
- `L2_small_hole_violation_ops.json` - 0.3mm hole (VIOLATED)
- `L2_stepped_shaft_ops.json` - Multi-diameter shaft
- `L2_thin_wall_violation_ops.json` - Thin-walled enclosure

### L3: Multi-Feature
- `L3_enclosure_ops.json` - Electronics enclosure
- `L3_gear_housing_ops.json` - Simple gearbox
- `L3_motor_mount_ops.json` - NEMA motor mount
- `L3_valve_body_ops.json` - 3-way valve body

### L4: Industrial (Iterative Refinement)
- `L4_aerospace_bracket_ops.json` - Aircraft hinge bracket (VIOLATED)
- `L4_aerospace_bracket_v2_ops.json` - Fixed design (PASS)
- `L4_gearbox_housing_ops.json` - Industrial gearbox (PASS with warnings)
- `L4_hydraulic_manifold_ops.json` - 6-port manifold (VIOLATED)
- `L4_hydraulic_manifold_v2_ops.json` - Fixed design (PASS)
- `L4_injection_mold_core_ops.json` - Mold insert (PASS with warnings)

### L5: Expert
- `L5_turbo_compressor_housing_ops.json` - Turbocharger housing (VIOLATED)
- `L5_turbo_compressor_housing_v2_ops.json` - Fixed design (PASS)

## Design Patterns Demonstrated

### 1. Deep Hole Mitigation
- Split long channels into intersecting shorter sections
- Use cross-drilling with plugs
- Switch to gun drilling process note

### 2. Small Feature Alternatives
- Replace micro-holes with larger holes + external fittings
- Use wire EDM for precision slots
- Cast-in features for complex internal shapes

### 3. Thin Wall Strengthening
- Add internal ribs
- Increase spacing between features
- Use alternative manufacturing (casting vs machining)

### 4. Sharp Corner Solutions
- Increase fillet radius (1/3 × depth minimum)
- Add dogbone/T-bone reliefs for mating parts
- Use EDM for critical sharp corners with cost note

## Adding New Test Cases

1. Create `LX_part_name_ops.json` with schema version `ops_program.v1`
2. Include `expected_findings` array documenting intended violations
3. For iterative refinement, create `LX_part_name_v2_ops.json` with fixes
4. Add `revision_notes` array explaining the changes
5. Run `run_all_demos.py` to validate
