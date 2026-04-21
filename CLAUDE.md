- In all interactions and commit messages, be extremely concise and
    sacrifice grammar for the sake of concision.
- Never include `Co-Authored-By` lines in commit messages.
- PROGRESS.md is where you write down what you've done.
- Before writing new features/functions always ask: is this necessary, has it been done, how will it interact with other modules?

## CAD Family Registry

Source of truth: `scripts/data_generation/cad_synth/pipeline/registry.py` (`list_families()`).
Current count: **106** registered families (as of 2026-04-19). Never quote family counts from stale commit messages or docstrings — always check `registry.py` or run `list_families()`.

## CAD Family Pre-Flight Rule (enforce before deploying any new family)

Before adding a new family to registry.py or starting a batch run:
1. Run 3–5 samples (easy/medium/hard mix) through the actual CadQuery build:
   ```bash
   export PATH="$HOME/.local/bin:$PATH" && LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 -c "
   import numpy as np; rng = np.random.default_rng(42)
   from scripts.data_generation.cad_synth.pipeline.registry import get_family
   from scripts.data_generation.cad_synth.pipeline.builder import build_from_program
   fam = get_family('FAMILY_NAME')
   for diff in ['easy','medium','hard']:
       p = fam.sample_params(diff, rng)
       if fam.validate_params(p):
           prog = fam.make_program(p)
           wp = build_from_program(prog)
           bb = wp.val().BoundingBox()
           print(diff, 'bbox', round(bb.xlen,1), round(bb.ylen,1), round(bb.zlen,1))
   "
   ```
2. Visually check: does the geometry match the family name? Are proportions physically plausible?
3. Check: no degenerate dims (flat, zero-volume, inverted), no part floating in space, no absurd scale.
4. Only after passing this check: register in registry.py and create/update batch config.

## Task Tracking (enforce always)

When the user assigns a task verbally, IMMEDIATELY do ALL of the following before any other work:
1. Write it to `TASK_QUEUE.md` under `## ⚠️ USER-ASSIGNED` with full details (what, why, how, reference code/URLs)
2. Write it to `.claude/projects/-workspace/memory/project_user_assigned_tasks.md`
3. Confirm to user: "已记录 UA-N: <one-line summary>"

Never say "I'll remember" without writing it down. Never start implementing before recording.

At the START of every session, read `TASK_QUEUE.md` and report any open USER-ASSIGNED items.

When a task is done, mark it `✅ DONE (date)` in TASK_QUEUE.md — do NOT delete it.

## Harness Rules (enforce these always)

### Honest Verification
- Never write "verified" without showing what you actually checked: file, line/value, result.
- Format: `CHECKED: <file>:<line> → <actual value> → PASS/FAIL`
- Never use phrases like "this will become X" or "for consistency" to skip showing the actual check.
- If you don't know, say "I don't know" — don't infer a plausible-sounding answer.

### Error Scan Protocol
- After finding one error, keep scanning. Stop only when 2 consecutive full passes find zero new issues.
- State pass count: "Pass 1: found N issues. Pass 2: found 0. Pass 3: found 0. Done."

### Convention Anchoring
- Before any edit that involves a naming/style/API convention, quote the relevant rule from CLAUDE.md verbatim.
- If no rule covers the case, flag it: "No convention found for X — defaulting to Y."

### Scope Pinning
- At task start, list the exact files and functions in scope.
- Any change outside that scope requires explicit user approval before proceeding.

### Anti-Sycophancy
- If you change your answer because the user pushed back (not because they gave new information), flag it:
  "Changing due to pressure, not new evidence."
- Maintain your position if it is correct; update it only when given a concrete reason.

## CAD Data Pipeline Report Format

When reporting pipeline status, ALWAYS include these columns in order:

1. **Data source** — Fusion360 N, DeepCAD N (separate counts)
2. **Verified total** — total rows in verified_parts.csv, delta since last report
3. **norm_step_path** — filled / missing
4. **norm_cq_code_path** — filled / missing (and why: exec_fail / low_iou / skip)
5. **views_raw_dir** — filled / missing
6. **Manual fixes** — total `_claude_fixed`, new this session
7. **Parts status** — verified / manually_fixed / near_miss / failed counts
8. **failure_code breakdown** — every labeled type + count (from parts.csv)
9. **retry_reason breakdown** — pending retry counts

Pull live stats:
```bash
export PATH="$HOME/.local/bin:$PATH" && LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 - << 'EOF'
import pandas as pd
vdf = pd.read_csv("data/data_generation/verified_parts.csv")
pdf = pd.read_csv("data/data_generation/parts.csv")
for col in ["norm_step_path","norm_cq_code_path","views_raw_dir"]:
    if col in vdf.columns:
        f = (vdf[col].notna() & (vdf[col]!="")).sum()
        print(f"{col}: {f}/{len(vdf)}")
print("manual fixes:", vdf["stem"].str.contains("_claude_fixed",na=False).sum())
print(pdf["status"].value_counts().to_string())
if "failure_code" in pdf.columns:
    print(pdf[pdf["failure_code"].notna()&(pdf["failure_code"]!="")]["failure_code"].value_counts().to_string())
if "retry_reason" in pdf.columns:
    print(pdf[pdf["retry_reason"].notna()&(pdf["retry_reason"]!="")]["retry_reason"].value_counts().to_string())
EOF
```

---

## CAD Data — File Map (ALWAYS use full relative paths, never bare filenames)

### DB tables (managed by `scripts/data_generation/db.py`)
| Path | Description |
|------|-------------|
| `data/data_generation/verified_parts.csv` | **Primary verified dataset** — iou≥0.99 records |
| `data/data_generation/verified/verified_pairs.jsonl` | JSONL mirror of verified_parts.csv |
| `data/data_generation/parts.csv` | Full stem registry — all runs, all statuses |
| `data/data_generation/operations.csv` | Per-stem operation log |
| `data/data_generation/runs.csv` | Per-run summary stats |
| `data/data_generation/fix_queue.csv` | Near-miss fix queue |

### Raw source data
| Path | Description |
|------|-------------|
| `data/data_generation/open_source/fusion360_gallery/raw/r1.0.1/reconstruction/` | Fusion360 reconstruction JSON files (`<stem>.json`) |
| `data/data_generation/open_source/fusion360_gallery/raw/r1.0.1_extrude_tools/extrude_tools/` | GT STEP files (`<stem>_<NNNNe>.step`) |

### Per-run codegen output (one dir per run)
| Path | Description |
|------|-------------|
| `data/data_generation/codex_validation/<run>/checkpoint.jsonl` | Per-stem results for that run |
| `data/data_generation/codex_validation/<run>/cadquery/<stem>.py` | Generated CadQuery code |
| `data/data_generation/codex_validation/<run>/generated_step/<stem>.step` | Generated STEP file |

### Rendered views
| Path | Description |
|------|-------------|
| `data/data_generation/views/<stem>/` | GT 4-view PNGs (`front.png`, `right.png`, `top.png`, `iso.png`) |
| `data/data_generation/views_gen/<stem>/` | Generated 4-view PNGs |

### SFT output
| Path | Description |
|------|-------------|
| `data/data_generation/sft/sft_img2cq.jsonl` | Image→CQ training pairs |
| `data/data_generation/sft/sft_json2cq.jsonl` | JSON→CQ training pairs |
| `data/data_generation/gencad/sft_gencad_img2cq.jsonl` | GenCAD img2cq pairs (162k) |

## Data Querying
- **Always use pandas to query CSVs/JSONL** — never read entire files manually line by line
- `pd.read_csv("data/data_generation/verified_parts.csv")` then filter with `.query()` / boolean indexing
- For JSONL: `pd.read_json("data/data_generation/verified/verified_pairs.jsonl", lines=True)` then filter
- Example: `df[df.iou < 0.999][["stem","iou","source"]].sort_values("iou").head(20)`

## CAD Data DB Sync (CRITICAL)
- **Primary source of truth: `data/data_generation/verified_parts.csv`**
- JSONL (`data/data_generation/verified/verified_pairs.jsonl`) is backup, kept in sync via `db.py`
- **Always write via `db.append_verified()`** — never write directly to JSONL alone
- **After any direct JSONL write, immediately rebuild CSVs:**
  ```bash
  export PATH="$HOME/.local/bin:$PATH" && LD_LIBRARY_PATH=/workspace/.local/lib uv run python3 scripts/data_generation/db.py
  ```

## Environment Setup
- Python environment managed with `uv`
- Install dependencies: `uv sync`
- Add new dependency: `uv add <package>`
- API keys live in `.env` (git-ignored):
  - `OPENAI_API_KEY` / `OPENAI_API_KEY1` — OpenAI (primary + rotation)
  - `OPENAI_MODEL` — default model (e.g. `gpt-5.2`)
  - `ZHIPU_API_KEY` — Zhipu AI (ZAI), fallback for data gen

## Synth Monitor UI

Streamlit app with 5 pages: Overview · Stem List · Stem Viewer · **Synth Monitor** · Eval

```bash
export PATH="$HOME/.local/bin:$PATH" && LD_LIBRARY_PATH=/workspace/.local/lib \
  uv run streamlit run scripts/data_generation/ui/app.py --server.port 8501
```

**Synth Monitor** tab: family distribution, difficulty breakdown, render previews, param tables, QA scores.
Do NOT build a separate CAD family preview UI — use Synth Monitor instead.

---

## Commands
```bash
uv run pytest                  # Run tests
uv run pytest tests/test_<name>.py  # Single test file
uv run black .                 # Format
uv run ruff check .            # Lint
uv run ruff check --fix .      # Lint + auto-fix
```

## Pre-Commit Checklist

**Run before every commit:**
1. `uv run black .`
2. `uv run ruff check .`
3. `uv run pytest`
4. Update `PROGRESS.md`

Only commit if all pass. Never include `Generated with Claude Code` in commits.

## Task Completion Rules
- **Run `uv run pytest` before marking any task done** — no exceptions
- **Update `PROGRESS.md`** after each completed task
- If tests fail, fix before proceeding

## File Paths
- Always use **relative paths** in: JSONL records, docs, config files, pipeline outputs
- Absolute paths only in: runtime env vars, subprocess invocations

## Code Style
- Format with black (default settings), lint with ruff
- snake_case for functions/vars, PascalCase for classes, UPPER_SNAKE for constants
- Imports sorted alphabetically (ruff I001)
- Use `is True`/`is False` not `== True`/`== False` (ruff E712)
- Test files: `tests/test_*.py`, function names: `test_<what>_<expected_behavior>`

## Evaluation Suite - IMPORTANT

**DO NOT read files under `tests/test_tools/test_cadquery/evaluation_suite/eval/`**

Held-out test samples — reading contaminates eval metrics. Safe alternatives:
- Read `eval_traces/` (execution results)
- Read `evaluation_suite/train/` (train samples)
- NEVER read `ground_truth.py`, `intent.txt`, or `spec.json` from `eval/`

## Plans
- At the end of each plan, give me a list of unresolved questions.
  Make questions extremely concise. Sacrifice grammar for concision.
