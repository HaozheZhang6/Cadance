# Cadance Bench — quickstart

Zero local-data dependency: clone → `uv sync` → `.env` → 一行命令从 HF 拉数据直接 eval。四种 bench task，两个 HF repo：

| Task | HF repo | 输入 → 输出 |
|------|---------|------------|
| **Code bench** | [`BenchCAD/cad_bench`](https://huggingface.co/datasets/BenchCAD/cad_bench) | image → CadQuery → exec + IoU/Chamfer/Feature-F1 |
| **QA bench (image)** | [`BenchCAD/cad_bench`](https://huggingface.co/datasets/BenchCAD/cad_bench) | image + 数值问题 → 数字数组 → ratio acc |
| **QA bench (code)** | [`BenchCAD/cad_bench`](https://huggingface.co/datasets/BenchCAD/cad_bench) | gt_code + 数值问题 → 数字数组 → ratio acc |
| **Edit bench** | [`BenchCAD/cad_bench_edit`](https://huggingface.co/datasets/BenchCAD/cad_bench_edit) | orig_code + NL 指令 → 修改后 code → norm_improve |

---

## 0. 一键启动（fresh machine）

```bash
git clone <repo> Cadance && cd Cadance

# 1. install (GPT eval 不需要 vtk；只有要 re-render 才加 --extra vision)
uv sync                           # GPT code+QA+edit eval 够用
# uv sync --extra vision          # 需要 --save-render / 重新 upload 数据时再加

# 2. set keys
cp .env.example .env
# edit .env: OPENAI_API_KEY=sk-... + (optional) BenchCAD_HF_TOKEN=hf_...

# 3a. Code bench — image → CadQuery → exec → IoU/CD
uv run python bench/test/run_test.py --limit 12 --model gpt-4o --save-code

# 3b. QA bench (image)
uv run python bench/eval_qa.py --limit 12 --model gpt-4o

# 3c. QA bench (code)
uv run python bench/eval_qa_code.py --limit 12 --model gpt-4o

# 3d. Edit bench — orig_code + instruction → modified code
uv run python -m bench.edit_gen.run_edit --model gpt-4o --n 10
uv run python -m bench.edit_gen.score_edit --model gpt-4o
```

默认 `--repo BenchCAD/cad_bench`（edit 走 `BenchCAD/cad_bench_edit`）+ `--split test`，都不用传。

Outputs：
- `bench/test/data/<stem>/composite.png` + `meta.json` — 从 HF 下的 GT
- `bench/test/results/<stem>/gen_code.py` — 模型生成的 CadQuery
- `bench/test/results/<stem>/gen_render.png` — 生成代码 exec+render (可选 `--save-render`)
- `bench/test/results/results.jsonl` — 逐样本 metric
- `bench_edit_runs/<model>/` — edit bench 输出（`gen_code/`, `gen_step/`, `results.jsonl`, `scored.jsonl`）
- stdout — overall summary

---

## 1. 环境要求

- Python ≥3.11, `uv`
- `.env`：
  - `OPENAI_API_KEY` — 跑 GPT
  - `BenchCAD_HF_TOKEN` / `HF_TOKEN` — public repo 可省
- **vtk 什么时候需要？** 只在要**渲染**时：
  | 场景 | 需要 vtk？ |
  |------|-----------|
  | GPT 拉 HF composite + 生成 code + 算 IoU/CD | ❌（image 已预渲染；IoU 用 trimesh） |
  | GPT QA eval | ❌ |
  | Edit bench (run_edit + score_edit) | ❌ |
  | Local VLM (cadrille 等) 推理 | ❌ |
  | `--save-render` (回渲 gen STEP 可视化) | ✅ `uv sync --extra vision` |
  | 上传新 bench 批次 (`push_bench_hf.py` / `upload_curated_hf.py`) | ✅ |
- `LD_LIBRARY_PATH` 只在 Linux container 下 load OCCT；Mac fallback 到 `/workspace/.local/lib` 无害。

---

## 2. 核心组件

| 文件 | 作用 |
|------|------|
| `bench/dataloader/__init__.py` | `load_hf(repo, split)` → list[dict]；token 从 `BenchCAD_HF_TOKEN`/`HF_TOKEN`/`HUGGINGFACE_TOKEN` auto-load |
| `bench/models/__init__.py` | VLM dispatch。`call_vlm(model, pil_img, api_key)` — `gpt-*`/`o1`/`o3` 走 OpenAI，`local:<path>` 走 Qwen2-VL/2.5-VL |
| `bench/metrics/__init__.py` | `compute_iou` (voxel 64³), `compute_chamfer` (2048 pts), `extract_features` (regex), `feature_f1`, `qa_score` |
| `bench/eval.py` | Full code-bench runner (stratified sample, resume) |
| `bench/eval_qa.py` | QA-bench runner (image) |
| `bench/eval_qa_code.py` | QA-bench runner (code, text-only) |
| `bench/test/run_test.py` | E2E code smoke runner (fetch → verify → eval → summary, 逐样本 flush jsonl) |
| `bench/edit_gen/run_edit.py` | Edit bench runner (HF or local bench_dir) |
| `bench/edit_gen/score_edit.py` | Edit bench scorer (IoU-based norm_improve) |
| `scripts/data_generation/cad_synth/push_bench_hf.py` | synth_parts → HF (code+QA) |
| `bench/edit_gen/upload_curated_hf.py` | pairs_curated → HF (edit) |

---

## 3. HF 数据集 schema

### `BenchCAD/cad_bench` (test, 20176 rows)
```
stem, family, difficulty, base_plane,
feature_tags (json str), feature_count, ops_used (json str),
gt_code (CadQuery Python),
composite_png (HF Image, 268×268, cadrille 4-diagonal 视角),
qa_pairs (json str — list of {question, answer, type}),
iso_tags (json str — derived ISO values)
```

### `BenchCAD/cad_bench_edit` (test, 371 rows)
```
record_id, family, edit_type, difficulty, level, axis, pct_delta,
orig_value, target_value, unit, human_name, instruction,
orig_code (text), gt_code (text),
orig_step (bytes), gt_step (bytes),
iou_orig_gt, dl_est, source, axes_detail, pct_deltas
```

edit_type: `dim` (212) / `multi_param` (118) / `add_hole` (30) / `add_chamfer` (9) / `add_fillet` (2). 106 families 覆盖。

---

## 4. View alignment（Code + QA image bench）

输入给模型的 `composite_png` 和模型输出代码 re-render 出来的 `gen_render.png` 用**同一个** renderer `scripts/data_generation/render_normalized_views.py`：

- `CAMERA_FRONTS = [[1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1]]`（cadrille 约定）
- 2×2 composite，每视图 128+3px border = 134，总 268×268
- normalized 到 bbox center=[0.5,0.5,0.5], longest→[0,1]

`bench/models/__init__.py` 的 `SYSTEM_PROMPT` 按这组视角描述。改一边必须改另一边。

---

## 5. 跑别的 model / 全量

```bash
# Full code bench (~20 min on gpt-4o, 20k 样本可用 --per-family 限量)
uv run python bench/eval.py --model gpt-4o --out results.jsonl

# Stratified: 1 sample per family
uv run python bench/eval.py --model gpt-4o --per-family 1 --out results.jsonl

# Resume
uv run python bench/eval.py --model gpt-4o --resume --out results.jsonl

# Local Qwen2-VL checkpoint
uv run python bench/eval.py --model local:./checkpoints/cadrille-sft

# Full edit bench
uv run python -m bench.edit_gen.run_edit --model gpt-4o
uv run python -m bench.edit_gen.score_edit --model gpt-4o
```

---

## 6. 指标

### Code bench (`bench/eval.py` / `bench/test/run_test.py`)
- `exec_ok` — 生成代码能不能跑出 STEP（0/1）
- `iou` — voxel IoU (64³, filled)。算前 bbox center→[0.5]³, longest→[0,1]³ normalize
- `iou_rot` — (可选) rotation-invariant IoU；`--rot-invariant 6` 只 face-up，`--rot-invariant 24` 全 cube group。`detail_score` 用 `max(iou, iou_rot)`
- `chamfer` — bidirectional squared chamfer (2048 pts)，越低越好
- `feature_f1` — regex feature 集合 F1（hole/fillet/chamfer）
- `detail_score` — `0.4·iou + 0.6·feature_f1`

### QA bench (`bench/eval_qa.py` image / `bench/eval_qa_code.py` code)
- 每 sample 2-3 个 numeric Q（integer count / ratio / dim mm），由 `qa_generator.py` 按 family 生成
- Image runner: composite image + `QA_SYSTEM_PROMPT` + questions
- Code runner: `gt_code` + `QA_CODE_SYSTEM_PROMPT` + questions（纯文本）
- 输出：**严格 JSON array of numbers**（解析失败 `parse_fail`）
- 评分：`qa_score_single = min(pred, gt) / max(pred, gt)`，对称 [0,1]

### Edit bench (`bench/edit_gen/score_edit.py`)
- `exec_rate` — 生成代码能 exec（0/1）
- `iou_orig_gt` — baseline 相似度（orig 到 gt 本身有多近）
- `iou_gen_gt` — 编辑后 vs gt 的相似度
- `norm_improve = clip((iou_gen_gt - iou_orig_gt) / (1 - iou_orig_gt), 0, 1)`
- degenerate pair (iou_orig_gt > 0.99) 跳过 norm_improve 聚合

Summary 打印 overall + per-split/per-difficulty (code) / per-family (QA/edit)。

---

## 7. External bench (fusion360 + deepcad)

框架 sanity check：100 条人写的（非 synth）fusion360 / deepcad verified 样本。只 code bench 适用（外部数据无 qa_pairs）。

**Step 1 — 上传**（需要 `verified_parts.csv` + VTK）：

```bash
uv sync --extra vision
uv run python bench/upload_external.py \
    --repo Hula0401/cad_external_bench \
    --n-fusion 50 --n-deepcad 50
```

**Step 2 — 跑 bench**（任意机器）：

```bash
uv run python bench/test/run_test.py \
    --repo Hula0401/cad_external_bench --split test --limit 100 --model gpt-4o
```

---

## 8. 上传新批次（开发者）

```bash
# code + QA bench
uv run python scripts/data_generation/cad_synth/push_bench_hf.py \
    --batch batch_20k_apr20 --repo BenchCAD/cad_bench

# edit bench
uv run python bench/edit_gen/upload_curated_hf.py \
    --repo BenchCAD/cad_bench_edit
```
