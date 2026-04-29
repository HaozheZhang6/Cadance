# Cadance

CAD synthesis + benchmark research repo. Two subprojects:

| Subproject | Path | Purpose |
|---|---|---|
| **Data generation** | `scripts/data_generation/` | Synth CAD pipeline — 106 parametric families → renders + CadQuery + QA pairs → HF datasets |
| **Benchmarks** | `bench/` | Evaluate VLMs/LLMs on image→code, image→QA, code→QA, code-edit (zero local data, all on HF) |

---

## Quick Start

```bash
git clone <repo> Cadance && cd Cadance
uv sync                              # default — fine for bench
# uv sync --extra vision             # only if re-rendering CAD (vtk); see per-subproject README

cp .env.example .env                 # fill in OPENAI_API_KEY, HF_TOKEN (optional)

# one-shot prefetch (优先跑这一行: HF cache + 解包 edit bench 给 UI 直读)
uv run python bench/fetch_data.py    # 20143 + 336 rows, ~124MB; runner / UI 之后秒开
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

### UI (`scripts/data_generation/ui/app.py`)

```bash
uv run streamlit run scripts/data_generation/ui/app.py --server.port 8501
```

Six-page Streamlit app — sidebar navigates between them:

| Page | Use it for |
|---|---|
| **Overview** | repo-level counts: verified pairs, families, run history |
| **Synth Monitor** | per-batch family / difficulty distribution, render previews, QA score histograms |
| **Stem List** | filter / sort all stems by source / status / iou / family |
| **Stem Viewer** | single-stem deep dive: 4-view composite, GT vs gen STEP, code, QA, exec logs |
| **编辑 Bench** | review edit pairs (`pairs_curated` / `topup_final` / **`from_hf`** ← `bench/fetch_data.py` 解包) — orig vs GT side-by-side, edit GT in place, re-exec |
| **CQ Playground** | paste CadQuery code, exec in subprocess, render 4-view (no DB write) |

See `CLAUDE.md` "Synth Monitor UI" — do NOT build a separate family-preview UI; extend Synth Monitor instead.

---

## Common tools — single-source ⚠️

**Do NOT write a new render / IoU / op-extraction / exec script when one of these exists.** Always import the canonical implementation; if you find yourself copying logic into a new file, fix it in place. Duplicate scripts have caused view-alignment drift, IoU disagreement, and metric mismatches in the past.

| Function | Canonical module | API |
|---|---|---|
| Normalize STEP + cadrille 4-view render | `scripts/data_generation/render_normalized_views.py` | `render_step_normalized(step_path, out_dir)` |
| Voxel IoU + 24-rotation IoU | `bench/metrics/__init__.py` | `compute_iou(gt, gen)`, `compute_rotation_invariant_iou(...)` |
| Per-stem essential ops + Feat-F1 | `bench/research/canonical_ops.py` (loads `.yaml`) | `essential_pass(family, gen_ops)`, `feature_f1(...)` |
| CadQuery exec sandbox | `bench/eval.py` | `exec_cq(code, timeout=60) → (step_path, err)` |
| HF dataset loader | `bench/dataloader/__init__.py` | `load_hf(repo, split, token)` |
| Stratified sampling | `bench/sampling.py` | `sample_rows(rows, n, seed)` |
| Results dir (append-only, dedup by stem) | `bench/results.py` | `ResultsDir(task, model)` |
| Model adapter (LLM/VLM) | `bench/models/registry.py` + `providers/` | `get_adapter(name).generate(...)` |
| Per-family essential spec (config) | `bench/research/canonical_ops.yaml` | edit YAML, no code change needed |

**Camera convention** — fixed; do NOT re-derive in any other script:
```python
CAMERA_FRONTS = [[1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1]]   # cadrille
# 2×2 composite, 268×268, normalized bbox center→[0.5]³, longest→[0,1]³
```
Any prompt under `bench/models/prompts.py` describing image views must match this set; changing camera = changing prompts.

---

## .env keys

| Variable | Used by |
|---|---|
| `OPENAI_API_KEY` / `OPENAI_API_KEY1` | bench, data gen |
| `OPENAI_MODEL` | default model (e.g. `gpt-4o`, `gpt-5.2`) |
| `ZHIPU_API_KEY` | data gen fallback |
| `HF_TOKEN` | pull/push HF datasets |

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

### Add a new model provider

Drop one file under `bench/models/providers/<name>.py`:

```python
from bench.models.registry import register, ModelAdapter

@register("my-model", "my-model-mini")  # CLI name(s) — e.g. --model my-model
class MyAdapter(ModelAdapter):
    def call_img2cq(self, image, prompt) -> str: ...
    def call_qa(self, payload, prompt) -> str: ...
```

Then `bench/models/providers/__init__.py` auto-imports it. No runner changes.
Existing examples: `openai.py`, `anthropic.py`, `gemini.py`, `deepseek.py`, `mistral.py`, `xai.py`, `zhipu.py`, `local_hf.py`.

### Add a new CAD family

1. Drop `scripts/data_generation/cad_synth/families/<name>.py` exposing `sample_params`, `validate_params`, `make_program`.
2. Run the pre-flight smoke (see `CLAUDE.md` "CAD Family Pre-Flight Rule") — 3 difficulties × build → bbox sane.
3. Register in `scripts/data_generation/cad_synth/pipeline/registry.py`.
4. Visually verify via Synth Monitor.

### Run a synth batch

```bash
uv run python -m scripts.data_generation.cad_synth.pipeline \
  --config scripts/data_generation/cad_synth/configs/batch_20k_apr20.yaml
```

Configs in `cad_synth/configs/*.yaml` pin family list, per-difficulty counts, seed, output paths.

### Tests

- `tests/test_data_generation/` — pipeline / verified-pairs builder
- `tests/test_tools/test_cadquery/evaluation_suite/` — held-out eval samples (do **NOT** read `eval/`; see CLAUDE.md)

See `CLAUDE.md` for full repo conventions (family pre-flight, task tracking, report formats, data-path map, harness rules).

---

## Layout

```
scripts/data_generation/          # Synth CAD pipeline
  cad_synth/
    families/                     # 106 parametric CAD families
    pipeline/                     # registry, builder, runner, renderer
    configs/                      # batch run configs
  ui/app.py                       # Streamlit 6-page UI (Overview / Synth Monitor / Stem List / Viewer / Edit Bench / CQ Playground)
bench/                            # Benchmarks (img2cq / qa_img / qa_code / edit_code / edit_img)
  edit_gen/                       # Edit benchmark data gen + runners
  models/                         # Provider registry + prompts
data/data_generation/             # CSV/JSONL tables, renders, SFT pairs (git-ignored)
CLAUDE.md                         # Repo conventions (read this first)
TASK_QUEUE.md                     # User-assigned tasks + history
PROGRESS.md                       # Session log
```
