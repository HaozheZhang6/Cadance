# Cadance

Engineering design automation + CAD synthesis research repo. Three main subprojects:

| Subproject | Path | Purpose |
|---|---|---|
| **Data generation** | `scripts/data_generation/` | Synth CAD pipeline — 106 parametric families → renders + CadQuery + QA pairs → HF datasets |
| **Benchmarks** | `bench/` | Evaluate VLMs/LLMs on image→code, image→QA, code→QA (zero local data, all on HF) |
| **Intent pipeline** | `src/` | Hypergraph G→R→S intent refinement + CAD artifact gen + verification |

---

## Quick Start

```bash
git clone <repo> Cadance && cd Cadance
uv sync                              # default — fine for bench + intent pipeline
# uv sync --extra vision             # only if re-rendering CAD (vtk); see per-subproject README

cp .env.example .env                 # fill in OPENAI_API_KEY, HF_TOKEN (optional)
```

### Run benchmarks (zero local data — pulls from HF)

```bash
# 1. Image → CadQuery code (IoU / Chamfer / Feature-F1)
uv run python bench/eval.py            --model gpt-5.4 --limit 300 --seed 42

# 2. Image → numeric QA
uv run python bench/eval_qa_img.py     --model gpt-5.4 --limit 300 --seed 42

# 3. Code → numeric QA (text-only)
uv run python bench/eval_qa_code.py    --model gpt-5.4 --limit 300 --seed 42

# 4. Code edit (orig code + NL instruction → modified code)
uv run python -m bench.edit_gen.run_edit_code  --model gpt-5.4 --limit 200 --seed 42
uv run python -m bench.edit_gen.run_edit_img   --model gpt-5.4 --limit 200 --seed 42
uv run python -m bench.edit_gen.score_edit     --model gpt-5.4
```

- Results land in `results/<task>/<model>/` (gitignored), dedup'd by stem across runs.
- `N > 200` auto-stratifies to ≥1 sample per family.
- Plug new model = add `bench/models/providers/<x>.py` with `@register("name")`; no runner changes.

Details: [`bench/README.md`](bench/README.md).

### Run intent pipeline

```bash
uv run python -m src.cli --intent "Design a mounting bracket for a 5kg load" --auto
```

Details below under [Intent Pipeline](#intent-pipeline).

### Synth Monitor UI

Streamlit dashboard for data gen runs (family/difficulty distribution, render previews, QA scores):

```bash
uv run streamlit run scripts/data_generation/ui/app.py --server.port 8501
```

---

## .env keys

| Variable | Used by |
|---|---|
| `OPENAI_API_KEY` / `OPENAI_API_KEY1` | bench, intent pipeline, data gen |
| `OPENAI_MODEL` | default model (e.g. `gpt-4o`, `gpt-5.2`) |
| `ZHIPU_API_KEY` | data gen fallback |
| `HF_TOKEN` | pull/push HF datasets |
| `HYPERGRAPH_STORE_PATH` | intent pipeline state |

All keys live in `.env` (git-ignored). Data pipeline auto-loads via `python-dotenv`.

---

## Benchmarks (`bench/`)

Six runners, four task types, two HF repos:

| Task | Runner | HF repo | Input → Output |
|---|---|---|---|
| **img2cq** | `bench/eval.py` | `BenchCAD/cad_bench` | image → CadQuery → exec → IoU/Chamfer/Feature-F1 |
| **img2cq_test** | `bench/test/run_test.py` | `BenchCAD/cad_bench` | staged fetch+render+eval with disk cache |
| **qa_img** | `bench/eval_qa_img.py` | `BenchCAD/cad_bench` | image + numeric Qs → JSON[number] → ratio accuracy |
| **qa_code** | `bench/eval_qa_code.py` | `BenchCAD/cad_bench` | `gt_code` + numeric Qs → JSON[number] → ratio accuracy |
| **edit_code** | `bench/edit_gen/run_edit_code.py` | `BenchCAD/cad_bench_edit` | orig code + NL instruction → modified code |
| **edit_img** | `bench/edit_gen/run_edit_img.py` | `BenchCAD/cad_bench_edit` | orig code + 4-view image + NL instruction → modified code |

HF datasets:
- `BenchCAD/cad_bench` — 20143 rows, test split (UA-23 2026-04-23 revalidated, 100% exec-pass)
- `BenchCAD/cad_bench_edit` — 371 curated edit pairs, 106 families covered

Runner infra (all 6 share):
- `bench/models/registry.py` + `providers/` — plug-and-play model dispatch; `--model <name>` is all the CLI sees
- `bench/sampling.py` — deterministic `(rows, n, seed)` → same samples; N>200 stratifies ≥1 per family + proportional fill
- `bench/results.py` — `results/<task>/<model>/` append-only pool with `runs/<ts>__seed<S>__N<N>.json` provenance sidecar
- `bench/models/prompts.py` — all system/user prompts + parsers centralized

All view alignment follows cadrille convention: cameras at `[1,1,1] / [-1,-1,-1] / [-1,1,-1] / [1,-1,1]`, 2×2 composite 268×268, bbox normalized to `[0,1]³` centered at `[0.5,0.5,0.5]`.

Full docs: [`bench/README.md`](bench/README.md).

---

## Data generation (`scripts/data_generation/`)

Parametric CadQuery family registry → sample params → build → render 4-view composite → QA generator → HF upload.

- **Registry:** `scripts/data_generation/cad_synth/pipeline/registry.py` — 106 families (bolts, gears, brackets, knobs, springs, …). Call `list_families()` for current count; never trust docstrings.
- **Families:** `scripts/data_generation/cad_synth/families/*.py` — each defines `sample_params`, `validate_params`, `make_program`, ISO/DIN reference.
- **Renderer:** `scripts/data_generation/render_normalized_views.py` — VTK, cadrille 4-view diagonals, normalized bbox.
- **HF upload:** `scripts/data_generation/cad_synth/upload_bench_hf.py`, `bench/smoke_upload.py`.
- **Edit benchmark:** `bench/edit_gen/` — 2–5% param deltas → pairs of `orig_code` / `gt_code` for zero-shot edit eval.

### Primary data tables

| Path | Description |
|---|---|
| `data/data_generation/verified_parts.csv` | **Primary** — iou≥0.99 verified pairs |
| `data/data_generation/parts.csv` | Full stem registry (all runs, all statuses) |
| `data/data_generation/synth_parts.csv` | Synth samples (accepted / rejected / production) |
| `data/data_generation/sft/sft_img2cq.jsonl` | SFT pairs (image → CadQuery) |
| `data/data_generation/bench_edit/pairs.jsonl` | Edit benchmark pairs |

All CSV/JSONL queries should use pandas (`pd.read_csv(...).query(...)`).

### Pre-flight rule (new families)

Before registering any new family:

```bash
uv run python3 -c "
import numpy as np; rng = np.random.default_rng(42)
from scripts.data_generation.cad_synth.pipeline.registry import get_family
from scripts.data_generation.cad_synth.pipeline.builder import build_from_program
fam = get_family('FAMILY_NAME')
for diff in ['easy','medium','hard']:
    p = fam.sample_params(diff, rng)
    if fam.validate_params(p):
        wp = build_from_program(fam.make_program(p))
        bb = wp.val().BoundingBox()
        print(diff, 'bbox', round(bb.xlen,1), round(bb.ylen,1), round(bb.zlen,1))
"
```

Then visually verify via Synth Monitor. See `CLAUDE.md` for full protocol.

---

## Intent Pipeline (`src/`)

Hypergraph-based intent → specs → CAD artifact → verification. Not used for bench/data-gen; standalone subproject.

```bash
uv run python -m src.cli --intent "Design a mounting bracket for a 5kg load" --auto
```

6-step flow: G→R→S tree → contract extraction → pre-artifact gate (V0/V1/V3/V4) → artifact gen → mech verification → auto-refinement. Full diagram and options in earlier README history; key CLI commands:

```bash
uv run python -m src.cli --intent "..." --auto --verbose    # SAT details + per-contract
uv run python -m src.cli show-graph                         # inspect hypergraph state
uv run python -m src.cli dag-run --intent "..." --auto      # multi-agent orchestrator
mech-verify verify part.step -o ./output                    # standalone STEP verifier
```

Docs:
- [End-to-End Pipeline](docs/end_to_end/README.md)
- [Memory Layer](docs/MEMORY_LAYER.md) (mem0 + ChromaDB intent cache)
- [Mech Verifier](docs/MECH_VERIFIER.md) / [EDA Verifier](docs/EDA_VERIFIER.md)
- [Verifier Core](docs/VERIFIER_CORE.md)

---

## Development

```bash
uv run pytest                 # tests
uv run pytest tests/test_<name>.py
uv run black .                # format
uv run ruff check .           # lint
uv run ruff check --fix .     # lint + autofix
```

Pre-commit (enforced):
1. `uv run black .`
2. `uv run ruff check .`
3. `uv run pytest`
4. Update `PROGRESS.md`

See `CLAUDE.md` for full repo conventions (family pre-flight, task tracking, report formats, data-path map, harness rules).

---

## Layout

```
src/                              # Intent pipeline (hypergraph, verification, mech/eda verifiers)
scripts/data_generation/          # Synth CAD pipeline
  cad_synth/
    families/                     # 106 parametric CAD families
    pipeline/                     # registry, builder, runner, renderer
    configs/                      # batch run configs
  ui/app.py                       # Streamlit Synth Monitor
bench/                            # Three benchmarks (code / QA-image / QA-code)
  edit_gen/                       # Edit benchmark data gen
data/data_generation/             # CSV/JSONL tables, renders, SFT pairs (git-ignored)
docs/                             # Architecture docs
CLAUDE.md                         # Repo conventions (read this first)
TASK_QUEUE.md                     # User-assigned tasks + history
PROGRESS.md                       # Session log
```
