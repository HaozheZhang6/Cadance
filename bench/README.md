# Cadance Bench — quickstart

Zero local-data dependency: clone → `uv sync` → `.env` → one command pulls smoke dataset from HF and runs eval end-to-end. Two parallel tasks:

- **Code bench** — `image → CadQuery code`，再 exec + IoU/Chamfer/Feature-F1
- **QA bench** — `image + 数值问题列表 → 数字数组`，算 symmetric ratio accuracy

---

## 0. 一键启动（fresh machine）

```bash
git clone <repo> Cadance && cd Cadance

# 1. install (GPT eval 不需要 vtk；只有要 re-render 才加 --extra vision)
uv sync                           # GPT code+QA eval 够用
# uv sync --extra vision          # 需要 --save-render / 重新 upload 数据时再加

# 2. set keys
cp .env.example .env
# edit .env: OPENAI_API_KEY=sk-... and HF_TOKEN=hf_...

# 3a. Code bench — image → CadQuery → exec → IoU/CD
uv run python bench/test/run_test.py \
    --repo Hula0401/cad_synth_bench_smoke \
    --split test_iid \
    --limit 12 \
    --model gpt-4o \
    --save-code                    # 跳过 --save-render 则完全不需要 vtk

# 3b. QA bench — image + questions → numeric answers → ratio accuracy
uv run python bench/eval_qa.py \
    --repo Hula0401/cad_synth_bench_smoke \
    --split test_iid \
    --limit 12 \
    --model gpt-4o
```

Outputs:
- `bench/test/data/<stem>/composite.png` + `meta.json` — 从 HF 下的 GT
- `bench/test/results/<stem>/gen_code.py` — GPT 生成的 CadQuery
- `bench/test/results/<stem>/gen_render.png` — 生成代码执行 + 渲染的 composite（和 GT 用同一 `render_step_normalized` pipeline，268×268，cadrille 视角）
- `bench/test/results/results.jsonl` — 逐样本 metric (iou, chamfer, feature_f1, detail_score, errors)
- stdout — overall summary

---

## 1. 环境要求

- Python ≥3.11, `uv`
- `.env`：
  - `OPENAI_API_KEY` — 跑 GPT
  - `HF_TOKEN` — 拉 HF dataset（public 可省）
- **vtk 什么时候需要？** 只在要**渲染**时：
  | 场景 | 需要 vtk？ |
  |------|-----------|
  | GPT 拉 HF composite + 生成 code + 算 IoU/CD | ❌（image 已预渲染；IoU 用 trimesh） |
  | GPT QA eval                                 | ❌ |
  | Local VLM (cadrille 等) 推理                | ❌ |
  | `--save-render` (回渲 gen STEP 可视化)      | ✅ `uv sync --extra vision` |
  | 上传新 smoke 批次 (`smoke_upload.py`)        | ✅ |
- `LD_LIBRARY_PATH` 只在 Linux container 下 load OCCT；Mac fallback 到 `/workspace/.local/lib` 无害（subprocess 里才读，路径不存在 = 无影响）。

---

## 2. 核心组件

| 文件 | 作用 |
|------|------|
| `bench/dataloader/__init__.py` | `load_hf(repo, split)` → list[dict]；支持 `split="all"` 合并三个 test split |
| `bench/models/__init__.py` | VLM dispatch。`call_vlm(model, pil_img, api_key)` — 支持 `gpt-*` / `o1` / `o3` 走 OpenAI，`local:<path>` 走 Qwen2-VL/2.5-VL |
| `bench/metrics/__init__.py` | `compute_iou` (voxel 64³), `compute_chamfer` (2048 pts), `extract_features` (regex), `feature_f1` |
| `bench/eval.py` | Full code-bench runner（所有 split、stratified sample、resume） |
| `bench/eval_qa.py` | QA-bench runner（image + qa_pairs → numeric answers → qa_score） |
| `bench/test/run_test.py` | E2E code smoke runner（fetch → verify → eval → summary，逐样本 flush jsonl） |
| `bench/smoke_upload.py` | 把本地 synth_parts.csv 里挑 N × 3 diff stratified 打成 HF dataset（**需要本地数据**，只 generator 跑） |

---

## 3. 现成 HF 数据集

| Repo | splits | rows | 备注 |
|------|--------|------|------|
| `Hula0401/cad_synth_bench`       | test_iid / test_ood_family / test_ood_plane | ~994 | 完整 bench_1k_apr14 |
| `Hula0401/cad_synth_bench_smoke` | test_iid                                    | 12   | 4 family × 3 diff，smoke 用 |

每行 schema：
```
stem, family, difficulty, base_plane, split,
feature_tags (json str), feature_count, ops_used (json str),
gt_code (CadQuery Python),
composite_png (HF Image, 268×268, cadrille 视角),
qa_pairs (json str — list of {question, answer, type}),
iso_tags (json str — derived ISO values)
```

---

## 4. View alignment（重要）

输入给模型的 `composite_png` 和模型输出代码 re-render 出来的 `gen_render.png` 用**同一个** renderer `scripts/data_generation/render_normalized_views.py`：

- `CAMERA_FRONTS = [[1,1,1], [-1,-1,-1], [-1,1,-1], [1,-1,1]]`（cadrille 约定）
- 2×2 composite，每视图 128+3px border = 134，总 268×268
- normalized 到 bbox center=[0.5,0.5,0.5], longest→[0,1]

`bench/models/__init__.py` 的 `SYSTEM_PROMPT` 已按这组视角描述（UA-18）。不要改一边不改另一边。

---

## 5. 跑别的 model / 别的 dataset

```bash
# Full bench (994 samples，~20 min on gpt-4o)
uv run python bench/eval.py --model gpt-4o --split all --out results.jsonl

# Stratified: 1 sample per family
uv run python bench/eval.py --model gpt-4o --split all --per-family 1 --out results.jsonl

# Resume
uv run python bench/eval.py --model gpt-4o --split test_iid --resume --out results.jsonl

# Local Qwen2-VL checkpoint
uv run python bench/eval.py --model local:./checkpoints/cadrille-sft --split test_iid
```

---

## 6. 指标

### Code bench (`bench/eval.py` / `bench/test/run_test.py`)
- `exec_ok`   — 生成代码能不能跑出 STEP（0/1）
- `iou`       — voxel IoU (64³, filled)，[0,1]，越高越好
- `chamfer`   — bidirectional squared chamfer (2048 pts)，越低越好
- `feature_f1`— regex feature 集合 F1（hole/fillet/chamfer），[0,1]
- `detail_score` — `0.4·iou + 0.6·feature_f1`

### QA bench (`bench/eval_qa.py`)
- 每个 sample 2–3 个 numeric 问题（integer count / ratio / dim in mm），问题由 `qa_generator.py` 按 family 生成
- Model 输入：composite image + `QA_SYSTEM_PROMPT` + `questions: list[str]`
- Model 输出：**严格 JSON array of numbers**（解析失败计 `parse_fail`）
- 评分：`qa_score_single = min(pred, gt) / max(pred, gt)` — 对称，[0,1]
- `qa_score` per-sample = 平均；summary 输出 overall + per-family

Summary 打印 overall + per-split / per-difficulty (code) 或 per-family (QA)。

---

## 7. 上传新 smoke 批次（只开发者）

```bash
# 从 synth_parts.csv 采样 4 family × 3 diff = 12 rows，打包推 HF
uv run python bench/smoke_upload.py \
    --repo Hula0401/cad_synth_bench_smoke \
    --families bolt,bevel_gear,clevis_pin,ball_knob \
    --seed 42
```

`composite_png` 从 `render_dir/composite.png` 读 bytes → PIL → HF `Image()` feature，embedded 进 parquet shard（232 KB / 12 rows）。
