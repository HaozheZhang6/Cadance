# Integration Test Suite: Verification Enhanced Confidence

## Overview

Unified test harness validating that mech_verify enhances confidence in CAD design verification through:

1. **CadQuery Code Execution** - Ground truth CAD designs from evaluation suite
2. **Geometric Validation** - Baseline confidence from geometric property matching
3. **mech_verify Integration** - Enhanced confidence via verification findings
4. **Confidence Analysis** - Quantitative comparison of baseline vs enhanced confidence

## Test Structure

```
tests/test_integration/
├── conftest.py                              # Pytest fixtures, test case loader
├── fixtures/
│   ├── cadquery_executor.py                 # Execute CadQuery code, export STEP
│   ├── verification_runner.py               # Run mech_verify with configs
│   └── confidence_analyzer.py               # Compute confidence metrics
└── test_verification_enhanced_confidence.py # Main test suite
```

## Test Cases

### Evaluation Suite (20 cases across 4 difficulty levels)

**Level 1 (Easy)** - 6 cases
- L1_01: Simple box
- L1_02: Cylinder
- L1_03: Extruded rectangle
- L1_04: Extruded circle
- L1_05: L-shape
- L1_06: Sphere

**Level 2 (Medium)** - 6 cases
- L2_01: Box with hole
- L2_02: Cylinder with hole
- L2_03: Plate with holes
- L2_04: U-channel
- L2_05: T-bracket
- L2_06: Rounded box

**Level 3 (Hard)** - 5 cases
- L3_01: Counterbore plate
- L3_02: Flanged cylinder
- L3_03: Stepped shaft
- L3_04: L-bracket
- L3_05: Enclosure with bosses

**Level 4 (Expert)** - 3 cases
- L4_01: Heat sink
- L4_02: Pipe elbow
- L4_03: Bearing block

## Test Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ 1. LOAD TEST CASES                                      │
│    - Scan evaluation_suite/ directory                   │
│    - Load intent.txt, spec.json, ground_truth.py        │
│    - Parse expected geometric properties                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. EXECUTE CADQUERY CODE                                │
│    - CadQueryExecutor runs ground_truth.py              │
│    - Exports STEP file + manifest.json                  │
│    - Isolated subprocess execution (safety)             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. GEOMETRIC ANALYSIS                                   │
│    - GeometricAnalyzer loads STEP via OCCT              │
│    - Computes: volume, bbox, face/edge counts           │
│    - Compares against expected spec.json                │
│    - BASE CONFIDENCE = weighted geometric match score   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 4. BASELINE VERIFICATION                                │
│    - VerificationRunner (minimal config)                │
│    - Basic STEP ingestion + geometry checks             │
│    - Collect findings/unknowns                          │
│    - BASELINE VERIFICATION SCORE                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 5. ENHANCED VERIFICATION                                │
│    - VerificationRunner (full config)                   │
│      ✓ SHACL validation enabled                         │
│      ✓ External tools (FreeCAD, SFA)                    │
│      ✓ DFM rules                                        │
│      ✓ Assembly checks                                  │
│    - ENHANCED VERIFICATION SCORE                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 6. CONFIDENCE COMPARISON                                │
│    - ConfidenceAnalyzer computes:                       │
│      • Base confidence (geometric only)                 │
│      • Baseline verification confidence                 │
│      • Enhanced verification confidence                 │
│    - Compute delta = enhanced - baseline                │
│    - Analyze improvement factors                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 7. RESULTS AGGREGATION                                  │
│    - SuiteResults collects all ConfidenceMetrics        │
│    - By-level analysis                                  │
│    - Pass rates (base vs enhanced)                      │
│    - Generate comparison report JSON                    │
└─────────────────────────────────────────────────────────┘
```

## Key Metrics

### ConfidenceMetrics (per test case)

```python
@dataclass
class ConfidenceMetrics:
    test_case_id: str
    level: int

    # Geometric baseline
    base_confidence: float  # 0.0-1.0, geometric comparison only
    geometric_comparison: GeometricComparison

    # Verification scores
    baseline_verification_score: float   # Minimal checks
    enhanced_verification_score: float   # Full checks
    confidence_delta: float              # enhanced - baseline

    # Verification details
    verification_status: str             # PASS, FAIL, UNKNOWN
    finding_count: int
    fail_finding_count: int
    warn_finding_count: int
    unknown_count: int
```

### SuiteResults (aggregated)

- **Total cases**: 20
- **Avg base confidence**: Geometric matching only
- **Avg enhanced confidence**: With verification layer
- **Avg confidence delta**: Enhancement from verification
- **Pass rate (base)**: Cases with base_confidence >= 0.9
- **Pass rate (enhanced)**: Cases with PASS + enhanced_confidence >= 0.9
- **By-level breakdown**: Metrics grouped by difficulty level

## Expected Outcomes

### Hypothesis
Verification layer should:
1. **Enhance confidence** when design is correct (delta > 0)
2. **Reduce false confidence** when design has issues (delta < 0, reveals problems)
3. **Reduce unknowns** by providing additional evidence
4. **Scale with complexity** - larger impact on harder test cases

### Success Criteria
- ✓ All 20 test cases execute successfully
- ✓ Geometric validation provides reasonable baseline (>80% perfect matches)
- ✓ Verification adds evidence (reduces unknowns)
- ✓ Confidence delta correlates with verification findings
- ✓ No crashes or exceptions in verification pipeline

## Running Tests

### Full Suite
```bash
uv run pytest tests/test_integration/test_verification_enhanced_confidence.py -v
```

### Individual Tests
```bash
# Check suite execution
uv run pytest tests/test_integration/test_verification_enhanced_confidence.py::test_suite_execution -v

# Verify confidence enhancement
uv run pytest tests/test_integration/test_verification_enhanced_confidence.py::test_verification_enhances_confidence -v

# Check unknown reduction
uv run pytest tests/test_integration/test_verification_enhanced_confidence.py::test_verification_reduces_unknowns -v

# Generate comparison report
uv run pytest tests/test_integration/test_verification_enhanced_confidence.py::test_generate_comparison_report -v
```

### View Results
After running tests, comparison report saved to:
```
{tmp_path}/verification_comparison_report.json
```

Report structure:
```json
{
  "summary": {
    "total_cases": 20,
    "executed_cases": 20,
    "avg_base_confidence": 0.95,
    "avg_enhanced_confidence": 0.98,
    "avg_confidence_delta": 0.03,
    "pass_rate_base": 0.85,
    "pass_rate_enhanced": 0.90
  },
  "by_level": {
    "level_1": {...},
    "level_2": {...},
    "level_3": {...},
    "level_4": {...}
  },
  "detailed_results": [...]
}
```

## Dependencies

### Required
- pytest >= 7.0
- cadquery >= 2.0 (for ground truth execution)
- src.mech_verifier.mech_verify (verification orchestrator)
- src.verifier_core (models, adapters)
- OCP (OpenCascade Python bindings for STEP I/O)

### Optional
- pyshacl (for SHACL validation in enhanced mode)
- FreeCAD (external tool adapter)
- NIST SFA (PMI analysis)

## Known Issues

### CadQuery/numpy Compatibility
CadQuery 2.x has compatibility issues with numpy 2.x (np.bool8 deprecated).

**Workaround options:**
1. Pin numpy to 1.x: `uv add "numpy<2.0"`
2. Use build123d instead of CadQuery
3. Run CadQuery in isolated conda environment

### External Tool Availability
Tests gracefully skip if external tools unavailable:
- FreeCAD: Emits Unknown if not found
- SFA: PMI checks disabled if not available

## Architecture

### Fixtures (conftest.py)

**evaluation_suite_dir**
- Scope: session
- Returns: Path to evaluation_suite/
- Scans for level_*/ directories

**test_cases**
- Scope: session
- Returns: list[EvaluationTestCase]
- Loads all 20 test cases with metadata

**cadquery_tool**
- Scope: session
- Returns: CadQueryExecutor
- Subprocess-based execution with timeout

**verification_orchestrator**
- Scope: session
- Returns: VerificationRunner (baseline config)
- Minimal checks for baseline score

**verification_orchestrator_enhanced**
- Scope: session
- Returns: VerificationRunner (enhanced config)
- Full checks including SHACL, external tools

**confidence_calculator**
- Scope: session
- Returns: ConfidenceAnalyzer
- Computes confidence from verification results

### Test Functions

**test_suite_execution**
- Validates all cases executed successfully
- Asserts: executed_cases == total_cases

**test_verification_enhances_confidence**
- Compares avg_base vs avg_enhanced confidence
- Prints delta summary

**test_verification_reduces_unknowns**
- Checks that unknowns are minimized
- Asserts: avg_unknowns < 5.0

**test_geometric_validation_baseline**
- Validates ground truth produces correct geometry
- Asserts: >80% perfect geometric matches

**test_pass_rate_by_level**
- Breaks down pass rates by difficulty level
- Shows confidence improvement per level

**test_generate_comparison_report**
- Generates comprehensive JSON report
- Includes summary, by-level, detailed results

## Future Enhancements

1. **Parametric variation testing**
   - Modify design parameters systematically
   - Validate confidence scales with deviation

2. **Failure injection**
   - Introduce geometric defects
   - Verify confidence drops appropriately

3. **Multi-backend comparison**
   - Test with CadQuery, build123d, FreeCAD
   - Compare verification consistency

4. **Performance benchmarks**
   - Track verification time per test case
   - Optimize slow verifications

5. **Integration with CI**
   - Automated test suite runs
   - Confidence trend tracking over commits

## References

- Evaluation suite: `tests/test_tools/test_cadquery/evaluation_suite/`
- mech_verify: `src/mech_verifier/mech_verify/`
- Fixtures: `tests/test_integration/fixtures/`
- Models: `src/verifier_core/verifier_core/models.py`

---

## New: Confidence Enhancement Infrastructure

Additional test infrastructure for confidence enhancement evaluation:

### New Fixtures (`fixtures/`)
- `cadquery_executor.py` - Safe CadQuery code execution
- `verification_runner.py` - Verification orchestration
- `confidence_analyzer.py` - Confidence score computation

### New Tests
- `test_confidence_infrastructure.py` - Infrastructure tests (no CadQuery dependency)
- `test_confidence_evaluation.py` - Full evaluation tests (requires CadQuery)

### Evaluation Script
See `scripts/run_confidence_evaluation.py` for batch evaluation of STEP files.

### Documentation
See `docs/verification_enhancement.md` for detailed architecture and usage.
