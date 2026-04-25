# Scripts

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
