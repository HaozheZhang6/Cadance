# Evaluation Scripts

## run_confidence_evaluation.py

Evaluates confidence enhancement through verification by comparing baseline vs enhanced verification configurations.

### Usage

```bash
# Basic evaluation
python scripts/run_confidence_evaluation.py /path/to/step/files

# With custom output directory
python scripts/run_confidence_evaluation.py /path/to/step/files -o ./results

# With external tools (requires FreeCAD, SFA)
python scripts/run_confidence_evaluation.py /path/to/step/files --use-external-tools

# With PMI requirement
python scripts/run_confidence_evaluation.py /path/to/step/files --require-pmi

# Different output formats
python scripts/run_confidence_evaluation.py /path/to/step/files --format json
python scripts/run_confidence_evaluation.py /path/to/step/files --format csv
python scripts/run_confidence_evaluation.py /path/to/step/files --format both  # default

# Verbose output
python scripts/run_confidence_evaluation.py /path/to/step/files -v
```

### Options

- `input_dir`: Directory containing STEP files to evaluate
- `-o, --output`: Output directory for results (default: evaluation_results)
- `--baseline-only`: Run only baseline verification
- `--enhanced-only`: Run only enhanced verification
- `--use-external-tools`: Enable external tool adapters
- `--require-pmi`: Require PMI data in verification
- `--format`: Output format (json, csv, both)
- `-v, --verbose`: Verbose output

### Output Files

- `results_<timestamp>.json`: Full results in JSON format
- `results_<timestamp>.csv`: Summary results in CSV format
- `summary_<timestamp>.txt`: Human-readable summary statistics

### Example

```bash
# Evaluate test projects
python scripts/run_confidence_evaluation.py \
  src/mech_verifier/test_projects/cadquery_golden_pass/inputs \
  -o ./evaluation_results \
  --format both \
  -v
```

### Requirements

- pythonocc-core (for STEP file loading)
- Optional: rdflib, pyshacl (for SHACL validation)
- Optional: FreeCAD, NIST SFA (for external tool adapters)

### See Also

- [Verification Enhancement Documentation](../docs/verification_enhancement.md)
- [Test Integration Fixtures](../tests/test_integration/fixtures/)

## run_resume_from_ops_loop.py

Batch loop runner for:

`uv run python -m src.cli resume --from-step from-ops --only --dry-run`

Each iteration creates `data/logs/<timestamp>/` and writes:
- screenshots to `data/logs/<timestamp>/screenshots`
- command output to `data/logs/<timestamp>/resume_from_ops.log`
- pipeline highlights to `data/logs/<timestamp>/ops_gen_pipeline.log`

Global rolling log:
- `data/logs/ops_gen_pipeline_history.log` (append mode)

Failure behavior:
- non-zero exit **does not stop** loop, continues next iteration

Usage:

```bash
# infinite loop
uv run python scripts/run_resume_from_ops_loop.py

# run 20 times
uv run python scripts/run_resume_from_ops_loop.py --max-runs 20
```

## data_generation/build_sft_datasets.py

Builds SFT JSONL files for:
- multi-view drawings -> CadQuery code (`sft_img2cq.jsonl`)
- JSON descriptions -> CadQuery code (`sft_json2cq.jsonl`)

Usage:

```bash
# basic build (no CadQuery execution)
uv run python scripts/data_generation/build_sft_datasets.py

# with validation + STEP export via tools/cadquery executor
uv run python scripts/data_generation/build_sft_datasets.py --validate
```

Optional open-source sources can be configured in `data/data_generation/open_source/sources.json`.

## data_generation/render_orthographic_drawings.py

Renders orthographic SVG drawings (front/right/top) from STEP files with
overall dimensions derived from the bounding box.

```bash
uv run python scripts/data_generation/render_orthographic_drawings.py \
  --step /path/to/part.step \
  --out-dir data/processed/orthographic
```

## data_generation/download_open_source.py

Downloads open-source CAD datasets into `data/data_generation/open_source/downloads`.

```bash
uv run python scripts/data_generation/download_open_source.py \
  --dataset fusion360_reconstruction \
  --accept-license
```

## data_generation/fusion360_pipeline.py

End-to-end pipeline: Fusion360 reconstruction JSON -> deterministic JSON -> CadQuery -> STEP -> orthographic drawings.

```bash
uv run python scripts/data_generation/fusion360_pipeline.py --limit 200 --render
```
