# CadQuery Evaluation Suite

This directory contains the evaluation infrastructure for testing CAD code generation from natural language intents.

## Structure

```
test_cadquery/
├── evaluation_suite/              # 70 test parts across 4 difficulty levels
│   ├── train/                     # Training samples (50 tests, visible during development)
│   │   ├── level_1_easy/          # 12 basic primitives (box, cylinder, sphere, etc.)
│   │   ├── level_2_medium/        # 15 parts with face selection (holes, chamfers, fillets)
│   │   ├── level_3_hard/          # 13 multi-feature parts (flanges, brackets, enclosures)
│   │   └── level_4_expert/        # 10 complex parts (heat sink, pipe elbow, bearing block)
│   ├── eval/                      # Held-out evaluation samples (20 tests, 5 per level)
│   │   └── (same structure)
│   ├── manifest.json              # Split assignments and metadata
│   ├── DESIGN_GUIDE.md            # Design principles for creating test cases
│   └── generate_specs.py          # Generate spec.json from ground truth
├── harness/
│   └── runner.py                  # EvaluationHarness class
├── test_cadquery_tool.py          # Unit tests
└── test_comparator.py             # Comparator tests
```

Each test part contains:
- `intent.txt` - Natural language description of the part
- `spec.json` - Expected geometry properties (volume, bounding box, face/edge counts)
- `ground_truth.py` - Reference CadQuery code

---

## Test Suite Overview

| Level | Train | Eval | Total | Description |
|-------|-------|------|-------|-------------|
| Level 1 (Easy) | 12 | 5 | 17 | Single primitives (box, cylinder, sphere) |
| Level 2 (Medium) | 15 | 5 | 20 | Face selection & features (holes, chamfers, fillets) |
| Level 3 (Hard) | 13 | 5 | 18 | Multi-feature parts (flanges, brackets, enclosures) |
| Level 4 (Expert) | 10 | 5 | 15 | Complex assemblies (heat sink, pipe elbow, bearing block) |
| **Total** | **50** | **20** | **70** | |

### Train/Eval Split

- **Train (50 tests)**: Used for prompt optimization (DSPy demos) and development iteration
- **Eval (20 tests)**: Held-out test set for unbiased performance measurement

**Important**: Files in `eval/` should not be read during development to prevent overfitting. See CLAUDE.md for access restrictions.

---

### Complexity Score Breakdown

Each test's complexity score (5-15) is calculated from five dimensions:

| Dimension | Description | Range |
|-----------|-------------|-------|
| **API Breadth** | Number of distinct CadQuery APIs required | 1-5 |
| **Parameterization** | Complexity of dimension calculations | 1-3 |
| **Selection** | Face/edge selection difficulty | 1-3 |
| **Ordering** | Operation sequencing requirements | 1-3 |
| **Ambiguity** | Interpretation flexibility in intent | 1-3 |

---

## Running Evaluations

### Primary Method: Intent-to-CAD Pipeline

The main evaluation workflow uses the Intent-to-CAD pipeline with observability:

```bash
# Run on all training tests
uv run python -m src.cad.intent_decomposition.run_evaluation --all

# Run on specific levels
uv run python -m src.cad.intent_decomposition.run_evaluation --levels 1 2

# Run with optimized checkpoint
uv run python -m src.cad.intent_decomposition.run_evaluation --checkpoint latest --all

# Run on held-out eval split (final performance measurement)
uv run python -m src.cad.intent_decomposition.run_evaluation --eval-only --all
```

### Compare Performance

```bash
# Compare baseline vs optimized
uv run python -m src.cad.intent_decomposition.compare_traces baseline latest

# View trace summary
uv run python -m src.cad.intent_decomposition.observability.cli summary
```

For detailed performance metrics, see: `eval_traces/cad/intent_decomposition/`

### Unit Tests

```bash
# Run all unit tests (validates test suite structure)
uv run pytest tests/test_tools/test_cadquery/ -v
```

### Harness API (Programmatic Usage)

```python
from tests.test_tools.test_cadquery.harness.runner import EvaluationHarness
from src.tools.cadquery_tool import CadQueryTool

harness = EvaluationHarness(CadQueryTool(backend='mock'))
level_1_results = harness.run_level(1)
for r in level_1_results:
    print(f"{r.test_id}: {'PASS' if r.success else 'FAIL'}")
```

---

## Adding New Test Cases

1. Decide on split: add to `train/` for development, `eval/` for held-out testing
2. Create a directory under the appropriate level: `train/level_N_*/LN_XX_name/`
3. Add `intent.txt` with the natural language description (follow `DESIGN_GUIDE.md`)
4. Add `ground_truth.py` with reference CadQuery code
5. Generate `spec.json`:
   ```bash
   uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_specs.py
   ```
6. Update `manifest.json` if needed:
   ```bash
   uv run python tests/test_tools/test_cadquery/evaluation_suite/generate_manifest.py
   ```

**Key conventions** (see `DESIGN_GUIDE.md` for details):
- Default to XY workplane unless intent explicitly specifies otherwise
- Use specific dimensional language (width/depth/height, not ambiguous x/y/z)
- Ensure ground truth produces valid Solid with positive volume
