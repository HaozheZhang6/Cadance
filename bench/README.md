# Cadance Bench — quickstart

Zero local-data dependency: clone → `uv sync` → `.env` → 一行命令从 HF 拉数据直接 eval。六个 runner（四类 task），两个 HF repo：

| Task | Runner | HF repo | 输入 → 输出 |
|------|--------|---------|------------|
| **img2cq** (full) | `bench/eval.py` | `BenchCAD/cad_bench` | image → CadQuery → exec + IoU/Chamfer/Feature-F1 |
| **img2cq_test** (staged) | `bench/test/run_test.py` | `BenchCAD/cad_bench` | fetch→render→eval, disk-cached input |
| **qa_img** | `bench/eval_qa_img.py` | `BenchCAD/cad_bench` | image + 数值问题 → 数字数组 → ratio acc |
| **qa_code** | `bench/eval_qa_code.py` | `BenchCAD/cad_bench` | gt_code + 数值问题 → 数字数组 → ratio acc |
| **edit_code** | `bench/edit_gen/run_edit_code.py` | `BenchCAD/cad_bench_edit` | orig_code + NL 指令 → 修改后 code |
| **edit_img** | `bench/edit_gen/run_edit_img.py` | `BenchCAD/cad_bench_edit` | orig_code + 4-view img + NL 指令 → 修改后 code |

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

# 2.5 一键预拉 bench 数据 (两个 HF repo: 20143 + 336 rows; ~124MB STEP 解包给 UI)
#     - 填 ~/.cache/huggingface → runner 走本地缓存,无网延迟
#     - 解包 cad_bench_edit → data/data_generation/bench_edit/from_hf/
#       UI 编辑 Bench 页直接选数据源 "from_hf" 就能查
#     可省略 — runner 首次会自己拉; 但 UI 直读必须跑一次
uv run python bench/fetch_data.py

# 3a. img2cq_test (staged smoke: fetch + render verify + eval)
uv run python bench/test/run_test.py --model gpt-4o --limit 12 --seed 42 --save-code

# 3b. qa_img
uv run python bench/eval_qa_img.py --model gpt-4o --limit 12 --seed 42

# 3c. qa_code
uv run python bench/eval_qa_code.py --model gpt-4o --limit 12 --seed 42

# 3d. edit_code
uv run python -m bench.edit_gen.run_edit_code --model gpt-4o --limit 10 --seed 42
uv run python -m bench.edit_gen.score_edit --model gpt-4o
```

默认 `--repo BenchCAD/cad_bench`（edit 走 `BenchCAD/cad_bench_edit`）+ `--split test`，都不用传。

### Results layout

```
results/<task>/<model_slug>/
  results.jsonl            append-only, one line per sample, dedup key=stem|record_id
  codes/<key>.py           gen code per sample (img2cq / edit_*)
  steps/<key>.step         gen STEP (edit_*)
  renders/<key>/           gen renders (img2cq_test --save-render)
  runs/<ts>__seed<S>__N<N>.json   per-invocation provenance
```

- 同一 `(task, model)` 是单一 pool；换 seed/N 重跑只追加新样本，老样本自动跳过。
- 同一 `(task, seed, N)` → 取到的 sample 集合完全可复现。
- `N > 200` 自动 stratified：每 family 至少 1 条，剩余按比例 fill。
- `N ≤ 200` 走 shuffle+head（不强保 family 覆盖）。
- 不同 model 互不污染：`gpt-4o` 跑过的样本不会被 `gpt-5` 当成 done。

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
| `bench/fetch_data.py` | 一键预拉两个 HF repo + 解包 edit bench 给 UI 直读 (`from_hf` 数据源) |
| `bench/dataloader/__init__.py` | `load_hf(repo, split)` → list[dict] |
| `bench/sampling.py` | `sample_rows(rows, n, seed)` — 共用，N>200 自动 stratified（每 family ≥1） |
| `bench/results.py` | `ResultsDir(task, model)` — append-only pool, dedup by id key, 写 `runs/<ts>__seed_N>.json` sidecar |
| `bench/models/registry.py` | ModelAdapter ABC + `register()` + `get_adapter(name)` |
| `bench/models/providers/openai.py` | OpenAI adapter（`gpt-*`/`o1`/`o3`，max_tokens key 自适配） |
| `bench/models/providers/local_hf.py` | `local:<path>` 前缀 → Qwen2-VL / Qwen2.5-VL |
| `bench/models/prompts.py` | 全部 SYSTEM/USER 提示词 + `parse_qa_answers` + `strip_fences` |
| `bench/models/__init__.py` | back-compat shim：`call_vlm` / `call_vlm_qa` / `call_llm_qa_code` / `call_edit_code` / `call_edit_vlm` |
| `bench/metrics/__init__.py` | `compute_iou` (voxel 64³), `compute_chamfer`, `extract_features`, `feature_f1`, `qa_score` |
| `bench/eval.py` | img2cq full runner |
| `bench/test/run_test.py` | img2cq_test staged runner（disk-cached input） |
| `bench/eval_qa_img.py` | qa_img runner |
| `bench/eval_qa_code.py` | qa_code runner |
| `bench/edit_gen/run_edit_code.py` | edit_code runner |
| `bench/edit_gen/run_edit_img.py` | edit_img runner |
| `bench/edit_gen/score_edit.py` | edit bench scorer (IoU-based norm_improve) |
| `scripts/data_generation/cad_synth/push_bench_hf.py` | synth_parts → HF (code+QA) |
| `bench/edit_gen/upload_curated_hf.py` | pairs_curated → HF (edit) |

### 加新 model
1. 在 `bench/models/providers/` 新建 `<name>.py`；继承 `ModelAdapter`，实现 `generate(system, user_text, images, max_tokens)`
2. 用 `@register("model-name", ...)` 或 `@register_prefix("prefix:")` 标注
3. 在 `bench/models/providers/__init__.py` 加一行 `from . import <name>` 让 side-effect 注册触发
4. Runner 不需要任何改动 — `--model <name>` 直接可用

---

## 3. HF 数据集 schema

### `BenchCAD/cad_bench` (test, 20143 rows, 2026-04-23 UA-23 revalidated)
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

`bench/models/prompts.py` 的 `SYSTEM_PROMPT` / `QA_IMG_SYSTEM_PROMPT` / `EDIT_IMG_SYSTEM_PROMPT` 按这组视角描述。改 renderer 一边必须改 prompts 另一边。

---

## 5. 跑别的 model / 全量

```bash
# img2cq, stratified 300 (每 family ≥1)
uv run python bench/eval.py --model gpt-4o --limit 300 --seed 42

# 加跑 200 条 — 自动跳过已完成 stem，同 seed 同 N 子集复现
uv run python bench/eval.py --model gpt-4o --limit 500 --seed 42

# 换 model — 完全独立的 results/img2cq/gpt-5/ 目录
uv run python bench/eval.py --model gpt-5.2 --limit 300 --seed 42

# Local Qwen2-VL checkpoint
uv run python bench/eval.py --model local:./checkpoints/cadrille-sft --limit 200

# Edit bench
uv run python -m bench.edit_gen.run_edit_code --model gpt-4o --limit 200 --seed 42
uv run python -m bench.edit_gen.run_edit_img  --model gpt-4o --limit 200 --seed 42
uv run python -m bench.edit_gen.score_edit    --model gpt-4o
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

### QA bench (`bench/eval_qa_img.py` / `bench/eval_qa_code.py`)
- 每 sample 2-3 个 numeric Q（integer count / ratio / dim mm），由 `qa_generator.py` 按 family 生成
- `qa_img`: composite image + `QA_IMG_SYSTEM_PROMPT` + questions
- `qa_code`: `gt_code` + `QA_CODE_SYSTEM_PROMPT` + questions（纯文本）
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
    --model gpt-4o --repo Hula0401/cad_external_bench --split test --limit 100 --seed 42
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
