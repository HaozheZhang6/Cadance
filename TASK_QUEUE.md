# TASK QUEUE

---

## ⚠️ USER-ASSIGNED — 进行中

### UA-25 — cad_curated_722 gt_code 手改 + OCC 验证 + 推 v2 ✅ DONE (2026-04-27)

**结果:**
- 新 `cq_gui/` sandbox (gitignore) — 隔离 py3.11 + cadquery 2.7 + cq-editor 0.7 venv,不污染 repo cq 2.3
- 722 行 → 单 .py per case dump (META sentinel + gt_code body 可改) + `sync_back.py` 回写 parquet
- 5 高亮 family (cable_routing_panel/clevis/parallel_key/tapered_boss/z_bracket) 手改 20 行 + drop 2 坏 clevis (#10 #11)
- OCC 全量校验:**719/720 pass (99.86%)**,1 fail = `synth_double_simplex_sprocket_000579_s4420` (timeout)
- 20 改过 case 重 render 4-view (用新 gt_code → STEP → `render_normalized_views`)
- HF push **`Hula0401/cad_curated_722_v2`** (720 rows + `exec_ok`/`exec_reason`/`exec_dt_s` 三列)
- Discord 发分布长图 6 chunk + v2 chunk 1 (含 EDIT/OK badge)
- 详见 `PROGRESS.md` session 30

### UA-24 — 复杂 family 简化 + DeepCAD/Fusion360 补缺 family ✅ DONE (2026-04-27)

**结果:**
- registry 最终 **106 个 simple_*** = 21 part-style + 85 across 5 packs (profiles 30 / cylindrical 15 / blocks 15 / multi_stage 12 / sheet_sections 13)
- 每 family 带 `REF` 属性 (F360 stem 或 imagined rationale);预览 gallery `tmp/simple106_previews/GALLERY_simple106.png` (2400×44472) ref-on-left
- batch_simple21_apr27 (4200 → 3473 verified, 82.7%) + batch_simple85_apr27 (4250 → 4182, 98.4%)
- HF push 单 split 7655 rows → https://huggingface.co/datasets/BenchCAD/cad_bench_simple106
- F360 r1.0.1 (8626 jsons) + DeepCAD data.tar 落盘 `data/data_generation/open_source/`
- F360 138 + DeepCAD 53 = 191 张人工分 16 类驱动 pack 设计
- Discord webhook 实时进度 (5min loop)
- 详见 `PROGRESS.md` session 29

### UA-23 — apr20-20k 数据集全清 + HF 重推 + 本地↔HF align ✅ DONE (2026-04-23)

**结果：**
- hollow_tube apr20 坏样本(YZ/XZ 下 box+rect 切成两块板)33 行已删 + rm stem 目录
- hollow_tube.py standard 字段 `EN 10305 → EN 10219`(家族尺寸表本来就是 EN 10219),CSV 346 行回填
- apr20 rejected 2920 行从 `synth_parts.csv` 删除
- gid 全局重编 1..36176(原 985 duplicate gid 消除)
- 新增 sticky exec-cache 列:`code_exec_ok` / `code_exec_reason` / `code_exec_checked_at`(加入 `exporter.SYNTH_FIELDS`,不 push HF)
- `_upload_filter.revalidate_exec` 改造:cache-aware 跳过已检过,持久化到 CSV;增量 checkpoint `tmp/exec_cache_checkpoint.jsonl`(每 2000)防再丢
- 全量 exec 校验 20221 apr20 accepted:**20143 pass / 78 fail**(0.39%)
  - fail 分布:`double_simplex_sprocket` 50, `slotted_plate` 6, `motor_end_cap` 5, `stepped_shaft` 5, `torus_link` 4, `shaft_collar` 4, 其他 ≤2
  - reason:`Standard_Failure` 69 / `exec_timeout` 5 / `zero_volume` 4
- `HfApi.delete_repo(BenchCAD/cad_bench)` 删云端 → `push_bench_hf --workers 8` 全 revalidate 重推
- **align 核对:HF test split = 20143 行,local (accepted apr20 ∩ exec_ok=True) = 20143,stem set 双向 diff = 0**
- 备份:`synth_parts.csv.bak_ua23_{003145,011932,addcols}*` 三份
- 一个坑:第一轮 `_write_exec_cache` pandas LossySetitemError(float64 列 setitem 字符串),results 丢失 40 分钟;已改 map-based 向量化 + 增量 checkpoint,重跑成功

**未做(scope 外,下一任务):**
- `exporter._next_gid()` race condition 根治(用 flock / SQLite 分配 gid),避免未来再产 duplicate
- `exporter.py:87` `gt.step = gen.step` 让 IoU 校验自我通过的问题(与 apr20 无关,但是导致 hollow_tube 多 solid 进了 verified 的根因)
- 其他 family 在 YZ/XZ 下是否也有类似 base_plane-fragile 问题,未系统扫

### UA-23 — apr20-20k 数据集全清 + HF 重推 + 本地↔HF align (设计稿,落地见上面)

**任务：** apr20-20k (`batch_20k_apr20`) 数据集搞干净,删云端重 push `BenchCAD/cad_bench`,保证 HF 官方 repo 和本地 CSV align。

**用户决策：**
- gid 列重排(985 重复 gid,race condition 产物 → 重编 1..N)
- 清 rejected 行(apr20 scope 内 2920 行)
- 多 solid 不过滤(hollow_tube apr20 33 行已单独删,其余家族不动)
- HF 云端删了重 push(不留旧版本)
- **不 re-exec 验证**,信任 CSV `accepted` 标签

### UA-22 — Bench runner 通用化：即插即用 model + 固定 results/ 分任务落地 + 可复现分层采样 ✅ DONE (2026-04-22)

**结果：**
- 新增基础设施 5 文件：`bench/models/registry.py` + `providers/{openai,local_hf}.py` + `prompts.py` + `sampling.py` + `results.py`
- 重命名（git mv）：`eval_qa.py → eval_qa_img.py`, `run_edit.py → run_edit_code.py`, `run_edit_vlm.py → run_edit_img.py`
- 6 runner refactor：`bench/eval.py` (img2cq), `bench/eval_qa_img.py`, `bench/eval_qa_code.py`, `bench/test/run_test.py` (img2cq_test), `bench/edit_gen/run_edit_code.py`, `bench/edit_gen/run_edit_img.py`
- `--model` 强制 required；去掉 `--out`/`--resume`/`--per-family`；统一 `--limit/--seed/--split/--repo`
- Adapter 单一接口 `generate(system, user_text, images, max_tokens) → (text, err)`，runner 完全不知 provider 细节；加新 model = 加 `providers/<x>.py` 一行 `@register(...)`
- Sampling：N≤200 shuffle+head；N>200 stratified（每 family ≥1 + 比例 fill）；同 `(rows, n, seed)` 完全确定
- Results：扁平 pool/(task, model)，`results.jsonl` append-only dedup，`runs/<ts>__seed<s>__N<n>.json` sidecar
- Smoke 验证：3 model × 2 task × N=3 → 同 seed 完全一致跨 model/task；N=3 → N=5 自动 done=3/todo=2；不同 model 子目录隔离
- `pytest 83 pass`；新文件 ruff clean
- 未做（不在本任务范围）：Anthropic adapter（架构留好，需要时新加 providers/anthropic.py）；删除 `bench/test/results/` 旧目录（已不被新 runner 写，留给用户决定）

### UA-22 (设计稿，落地见上面 ✅ DONE 条目)

**动机：** 现 4 runner (`bench/eval.py` / `eval_qa.py` / `eval_qa_code.py` / `test/run_test.py`) `--model` 默认 `gpt-4o`，提供商/max_tokens 切换是在 runner 里 `startswith("gpt-5")` 硬判；结果默认 `bench/test/results/*.jsonl`，任务间易覆盖、无 skip；limit 仅随机 shuffle 不保证 family 覆盖。

**硬性要求：**

1. **Model 即插即用** — runner 里不准写死 model/provider。统一走 `bench/models/registry.py` 之类的 dispatch：CLI 只传 `--model`，runner 不做 `startswith("gpt-5")` 判定。Provider、max_tokens key、system prompt 选择都在 model adapter 里。新增 model = 注册一条 adapter，不改 runner。

2. **固定 results/ 目录 + 分任务子目录：**
   ```
   results/
     img2cq/       ← bench/eval.py
     vlm_qa/       ← bench/eval_qa.py
     code_qa/      ← bench/eval_qa_code.py
     img2cq_test/  ← bench/test/run_test.py
     edit/         ← 未来 edit runner
   ```
   每次运行产物（code/step/render/result.jsonl）落到 `results/<task>/<model>/<run_id>/`，run_id 由 (task, model, split, seed, N) 决定。

3. **不重复跑：** 每条 sample 按 `stem`（或 `rid` for edit）去重。runner 启动时扫 `results/<task>/<model>/` 下已完成 sample，跳过再拉新的补齐到 N。替换目前 `eval.py --resume` 的行为，扩到另外 3 个 runner。

4. **每任务独立随机采样方法（可复现）：**
   - 同一 `(task, seed, N)` → 取到的 sample 集合必须完全一致。
   - QA codegen (img + code)：**N ≤ 200**：纯 shuffle 取前 N；**N > 200**：stratified — 每 family 至少 1 条，剩余名额按 family 规模 proportional 再填。
   - Img2CQ：沿用现有 stratified_sample（已存在），但同样 seed → 同样采样结果。
   - Edit：按 `edit_type` + family 两级分层（L1/L2 各自保均匀）。
   - 采样函数抽到 `bench/sampling.py`，4 runner 共用。

**产出：**
- `bench/models/registry.py`（或扩现 `bench/models/__init__.py`）：model → adapter dispatch
- `bench/sampling.py`：`stratified(rows, n, seed, task)` 返回固定顺序 rows
- `bench/results.py`：`run_dir(task, model, ...)` + `load_done(run_dir)` 复用
- 4 runner 重构到新 results/ 路径 + 用 sampling.py + 去重
- `README.md` 一张新路径表

**不在范围：** 新增 eval metric、新增 model provider、edit runner 本身（等 UA-22 基础设施落地后再开 UA-23）。

**未解问题：**
- run_id 要不要包含 git sha（便于 trace code 版本 vs results）？
- `results/` 进不进 git？（预期 gitignore，只留 dir placeholder）
- 历史 `bench/test/results/*.jsonl` 迁移还是保留？

### UA-20 — Edit bench curated subset (每 family 1-2 个 low-coupling edit) ✅ DONE (2026-04-22)

**结果：** 371 pairs 落地 `pairs_curated.jsonl`（106 families 覆盖；edit_types: dim 212 / multi_param 118 / add_hole 30 / add_chamfer 9 / add_fillet 2）。同批推至 `BenchCAD/cad_bench_edit` (test split, 371 行)。Previews dir: 215 files.

**动机：** 现 724 pairs 很多编辑耦合太深（knob total_height 要改 33 个 magic number），模型不可能逆推公式。

**目标：** 每 family 手工挑 1-2 个 **低耦合** edit pair，模型能真正理解和执行。

**选 axis 优先级（user 指示）：**
- 后置无依赖的 feature：**fillet / chamfer / hole / bore 类**
- 主体尺寸（会 cascade）：除非 dl 很小，否则避免

**硬约束：**
- IoU(orig_step, gt_step) < 0.99（normalized 后不能 = 1，否则 edit 不可见）
- 每 family 1 个；能清晰分成 2 个不同 feature 的再加第 2 个；说不清的只 1

**产出：**
- `data/data_generation/bench_edit/pairs_curated.jsonl`（新文件，不覆盖 pairs.jsonl）
- `data/data_generation/bench_edit/previews/<family>.png`（orig | gt side-by-side，cadrille 4-view）
- 每 pair 汇报：改了哪个 param、orig_value → target_value、dl、iou

**执行计划：**
1. 识别每 family 可用的 low-coupling axes（从 edit_axes.py + rendered diff_lines）
2. 对 54 dl≤4 families：直接用现有 pair（优先挑 bore/chamfer/fillet 轴）
3. 对 50 dl>4 families：手动改 orig code 或补新 axis
4. 渲染 preview
5. 写 pairs_curated.jsonl

### UA-19 — Edit Benchmark data gen (1000-2000 pair, L1/L2, 小 delta) ✅ DONE (2026-04-20)

**结果：**
- 1228 pairs (L1×614 + L2×614) 落地 `data/data_generation/bench_edit/pairs.jsonl`
- 105 families（排除 worm_screw，UA-16 已知 OCCT 崩溃）; 97.5% yield (1228/1260 max)
- Per-family 产量极均匀：最低 bearing_retainer_cap 4 records（2 axis×2 level，另 2 axis variant-only skip），其他家族 6-12
- Filter 总丢失 12：validate×3, constraint×3, build×2, skip_not_in_root×4
- pair_builder 加了增量 flush（每 family 一刷）防 OCCT C 层崩溃丢数据；`--exclude` CLI flag
- 产物：`codes/` 820 个、`steps/` 820 个、`pair_stats.json`
- 遗留：worm_screw 待 UA-16 修复后补跑（~24 records 缺口）



**目标：** 生成一套独立的 CAD edit benchmark 数据集。模型输入：原始 CQ code + NL 指令；输出：修改后 CQ code。零训练，纯 zero-shot 评测。

**配置：**
- 范围：106 families 全量（registry.py `list_families()`）
- 每 family：2 roots (easy + hard) × 3 axes × 1 delta × 2 levels (L1/L2) = 12 records
- 总量目标：~1000-2000 pairs
- Delta 策略：**2-5% 小幅度 + 预选安全方向**
  - 内径/孔径 → 缩小 (-)
  - 外径/外框/长宽高/厚度 → 放大 (+)
  - 齿数/孔数 等离散/拓扑参数 → 不选
- L1: `"Set <human> to <value> <unit>."`（4 位小数）
- L2: `"Change <human> by <sign><pct>%."`

**产出：**
```
data/data_generation/bench_edit/
  pairs.jsonl
  codes/<rid>_{orig,gt}.py
  steps/<rid>_{orig,gt}.step
  pair_stats.json
```

**改动/新增：**
1. `bench/edit_gen/edit_axes.py` (新) — 106 家族 EDIT_AXES 中心化配置
2. `bench/edit_gen/pair_builder.py` (新) — 生成 pair + 写 STEP/code
3. `scripts/data_generation/cad_synth/pipeline/builder.py` — `render_program_to_code` 顶部加参数注释块（给模型语义 hint，不参数化代码本体）

**三层过滤（防翻车）：**
1. `fam.validate_params(p1)` — 家族内置约束
2. `check_axis_constraints(p1)` — axis 级 ordering (e.g. inner < outer)
3. `sanity_ok(step0, step1)` — post-build 几何 sanity（体积塌缩、bbox 爆炸）

**评分（本任务不含，eval 阶段实现）：** `norm_improve = (IoU(out,gt) - IoU(orig,gt)) / (1 - IoU(orig,gt))` + `exec_rate`

### UA-18 — Bench view alignment: GPT prompt + gen render 都走 cadrille 视角 ✅ DONE (2026-04-20)

**结果：**
- `bench/models/__init__.py` SYSTEM_PROMPT 改到 cadrille 对角视角 `[1,1,1]/[-1,-1,-1]/[-1,1,-1]/[1,-1,1]`
- `bench/test/run_test.py` `_render_step` 换成真 `render_step_normalized`（之前 import 的 `render_views` 根本不存在）
- GPT-4o 12 样本 e2e 跑通：composite (GT) 和 gen_render 都 268×268, 同 renderer, view 完全对齐
- 同批顺带做完：bench/smoke_upload.py schema +qa_pairs/+iso_tags 列；`bench/eval_qa.py` 新增；`bench/models/call_vlm_qa` 新增；`Hula0401/cad_synth_bench_smoke` 重推
- README 更新：`uv sync` 默认够 GPT eval，`--extra vision` 只 re-render 时必要

### UA-20 — QA bench runner (image + numeric Q → answers → ratio acc) ✅ DONE (2026-04-20)

**结果：** 见 UA-18 同一 session。`bench/eval_qa.py` + `QA_SYSTEM_PROMPT` + `call_vlm_qa` + HF schema `qa_pairs`/`iso_tags` 列。GPT-4o 12 样本 qa_score 0.562, parse 12/12。

### UA-21 — QA bench runner (code → numeric Q → answers) ✅ DONE (2026-04-20)

**结果：** 纯文本 LLM path，输入 `gt_code` + questions，输出 JSON 数字数组，复用 `qa_score`。
- 新 `bench/eval_qa_code.py` + `QA_CODE_SYSTEM_PROMPT` + `call_openai_qa_code` / `call_llm_qa_code`
- HF 数据复用既有 smoke（`gt_code` + `qa_pairs` 都已 embedded，无需重传）
- GPT-4o 12 样本 parse 12/12, qa_score 0.526；per-family: bolt 1.000 / ball_knob 0.854 / clevis_pin 0.250 / bevel_gear 0.000
- README 更新：三 bench 一键启动命令 + code-runner 说明

### UA-16 — 修 `worm_screw` medium+hard 变体 chamfer 后几何塌陷 🟠 MED (2026-04-19)

**现象：** 只要开启 `chamfer`（medium 起）就可能触发，某些参数下 bbox 的 z 从 sl 缩到 0.7–0.8×sl，视觉上整根光轴消失、只剩螺旋+端盘。hard 路径（bore+keyway）更严重：要么 bbox 塌到 ~5×13×4，要么直接 OCCT 原生崩溃。
**复现（medium，4 seed × 4 case）：**
- seed=42 medium (m=2, z1=1, d1=32, tl=25, sl=56.6, chamfer=1.0) → bbox 36×36×43.2（z 缩 13.4mm）
- seed=7 medium (m=4, z1=2, d1=40, sl=108.8, chamfer=0.5) → 光轴消失
- seed=777 medium → 光轴消失
- seed=123 medium (m=1, d1=8, sl=27.3) → 正常 ✓
**复现（hard）：** `default_rng(42)` 第 3 次 hard → bbox 4.94×12.96×4.21；`default_rng(7)` 第 3 次 hard → OCCT 进程崩溃（exit 无 trace）。
**Trace (hard s42)：** op[5]=chamfer(<Z,0.5) 后 z 已异常缩到 20.42（预期 24.0）；op[9]=hole(5.9) 把 bbox 打成 4.94×12.96×4.21。
**根因推测：** `union` 后 `sweep(helix, isFrenet=True)` 在螺纹端点处产生非流形边或额外面；`edges("<Z")`/`edges(">Z")` 选到螺纹端面而非轴底/顶圆边，chamfer 把螺纹整段削掉。
**影响范围：** medium 约 3/4 随机 seed 坏；hard 几乎全坏。easy（无 chamfer）不受影响。gid 4078 (medium) 参数偏小（d1=6.5→8）运气好没塌。
**修复方向：** (a) sweep 前后对 shaft 和 thread 分别 `clean()`/`fuse()`；(b) chamfer 用 `.faces(">Z").edges()` / tag 路径而不是全局 `edges(">Z")`；(c) hole/keyway 走绝对 workplane 而非链式 `.faces(">Z").workplane()`。

### UA-15 — 新增 3 family: `wing_nut` / `star_knob` / `grease_nipple` ✅ DONE (2026-04-19)

**结果：**
- 3 个 family (wing_nut/DIN 315, star_knob/DIN 6336, grease_nipple/DIN 71412 H1) 全部注册；总 family 88→91
- 初筛 communication.md 5 候选 → skip grooved_pin (与 dowel/clevis/taper_pin 重合) + lifting_eye_nut (与 eyebolt 重合)
- Manual 原型 3 份 → Op 化 → pre-flight 9/9 → roundtrip 27/27 (3 fam × 3 diff × 3 seed) bbox 完全 match → 9/9 composite PNG 视觉 OK
- 关键坑：star_knob union 后 top 面只 5 凹谷 edges，OCCT 任意 r fillet/chamfer 都 fail → 完全移除 top/bottom fillet；`_apply_op` 的 fillet try/except 会静默吞错 → 必须 roundtrip 验证才暴露
- grease_nipple validate 修正：`s*2/sqrt(3) > d` 而非 `s > d`（pipe thread d>AF）；R1/4 s=11→14
- 88 data_gen tests pass；ruff clean；black clean

### UA-17 — 新增 `twisted_joint` family (eye-plate 扭转接头) ❌ REMOVED (2026-04-19)

**状态：** 2-section loft 产物被用户判定为"根本不是 twisted"（直纹 wedge 不是平滑螺旋扭面）。走真正平滑扭转需新增自由-API Op (`Face.Reversed` + `loft(parametrization="chordal")` + 4 段 eps 夹心 loft)。决定直接移除，不保留半成品。

### UA-14 — 新增 `twisted_drill` family (DIN 338 麻花钻) ✅ DONE (2026-04-19)

**结果：**
- 第 87 个 family `twisted_drill` 注册 (pipeline/registry.py)
- 新增 4 Op + renderer：`sketch_subtract` / `placeSketch` / `twistExtrude` / `intersect`
- Sketch 跨 Op 通过 `_pending_sketch` / `_pending_sketch_code` 模块级 state 串连（同 `_current_base_plane` 模式）
- 关键改动：OCCT `body.intersect(cone_envelope)` intermittent Bnd_Box 崩溃 → 改 `body.cut(big_cyl ∖ envelope)` tip-chimney
- 采样约束：`total_twist = 360·(L+5)/P < 340°`；`L/P < 0.87`；R0 ∈ {2,2.5,3,4,5,6,8}mm；tip_angle ∈ {118,130,140}°
- 全 hard 难度（用户指定）；standard="DIN 338"
- 5 seed render→exec bbox 全 PASS；15/15 random hard 样本 build pass；88 data_gen tests pass；ruff + black clean

**流程：** Op 扩展 → family 文件 → Pre-Flight 3-sample 测试 → 注册 → pytest/black/ruff → PROGRESS.md。

### UA-13 — 新增 `twisted_bracket` family (无 ISO 参考) ✅ DONE (2026-04-18)

**目标：** 加一类 twisted_bracket family，无 ISO 约束，只需物理/常识合理。
**参考：** `tmp/manual_family_previews/manual_twisted_bracket.py`（两块垂直薄板 + 短螺旋 loft 连接）
**结果：**
- `twisted_bracket` — 两块互相垂直的平板沿 X 轴侧并排，中间 YZ-loft 90° 扭转连接
- Plate 1: XY 平面（厚度 Z）；Plate 2: XZ 平面（厚度 Y，-90°X 旋转）
- loft 端面：rotate[0,90,0] + chained rotate[0,0,90] 实现扭转
- 每板 1 或 2 个螺栓孔（沿长度均分）
- 3×3 preflight 8/9 通过（1/9 参数随机组合触发边距 validate 拒绝）；18-sample batch 100% 通过

### UA-12 — 新增 4 family: eyebolt / spline_hub / venturi_tube / torsion_spring ✅ DONE (2026-04-18)

**目标：** 将 4 个 manual 原型转为 registered families
**参考：** `tmp/manual_family_previews/manual_{eyebolt,internal_spline_hub,venturi_tube,torsion_spring}.py`
**结果：**
- `eyebolt` (DIN 580) — collar+shank+neck-loft+torus eye；新增 `torus` Op
- `spline_hub` (DIN 5480) — hub+内齿切削(threePointArc×4z)+undercut+chamfer
- `venturi_tube` (ISO 5167-4) — 闭合截面沿 Y revolve 360°
- `torsion_spring` (DIN 2088) — 已存在，本次仅注册
4/4 family 3×3 preflight 全通过 + 视觉审核通过 + registry 注册。

### UA-11 — 新增 `torsion_spring` family (DIN 2088) ✅ DONE (2026-04-18)

随 UA-12 一并完成。family 文件已在 UA-11 前期实现，UA-12 完成注册。

### UA-10 — 新增 `roller_chain` family + 精修 prposal.md 🔴 HIGH (2026-04-18)

**目标：**
1. 对照现有 80 families 精修 `prposal.md`（删 `clevis_pin` 重复；`compression_spring` 改为升级现有 `coil_spring`）。✅ DONE
2. 新增 `roller_chain` family 配对现有 `sprocket` / `double_simplex_sprocket`。

**`roller_chain` 设计要点 (ISO 606):**
- chain code 与 sprocket 共享：`06B-1`, `08B-1`, `10B-1`, `12B-1`, `16B-1`, `20B-1`
- 表列：pitch $p$, roller $d_1$, inner width $b_1$, pin $d_2$, plate height $h_2$
- 单 link = 外板×2 + 内板×2 + 销×2 + 套筒×2 + 滚子×2
- 8 字链板：两圆弧 ($h_2/2$) + 两切线 → polyline 封闭轮廓 → 拉伸
- N_links pattern 沿 X 轴，内外板交替
- 与 sprocket pitch 锁定 → 可渲染 sprocket+chain 驱动组合（未来）

**流程（遵循 CLAUDE.md CAD Family Pre-Flight Rule）：**
1. 在 `tmp/manual_family_previews/manual_roller_chain.py` 写算法原型
2. 视觉 OK 后搬入 `families/roller_chain.py`
3. 3×3 preflight (easy/medium/hard × 3 trials) 全通过
4. 注册到 `registry.py`
5. `AUDIT_METHODOLOGY.md` 的 9 步视觉审核
6. 更新 `PROGRESS.md` + 标记 UA-10 ✅ DONE


### UA-6 — ISO 标准化 family 脚本升级 ✅ DONE (2026-04-18)

**目标：**
- 每个有标准的 family 的参数化生成逻辑必须真正符合工业标准：
  1. 参数从标准尺寸表采样（离散值），不是连续随机
  2. 关键比例/公式关系要在代码里体现
  3. `iso_tags` / `qa_pairs` 在 qa_generator.py 里要有对应条目
- 工作流：先在 `tmp/manual_family_previews/manual_<family>.py` 生成预览，目测 OK 后再改 family 脚本

**优先级（按"能做到离散表驱动"的强度排序）：**

Tier 1 — 强约束件，直接查表：
| Family | 标准 | 状态 |
|--------|------|------|
| hex_nut | ISO 4032 | ✅ 已有精确表格 |
| bolt | ISO 4014 + ISO 888 | ✅ 已有精确表格 |
| plain_washer | ISO 7089/7090 | ✅ 已有精确表格 |
| dowel_pin | ISO 8734 | ✅ 已有精确表格 |
| taper_pin | ISO 2339 | ✅ 已有精确表格 |
| parallel_key | DIN 6885A | ✅ 已有精确表格 |
| shaft_collar | DIN 705 | ✅ 已有精确表格 |
| circlip | DIN 471/472 | ✅ 精确DIN 471表 2026-04-18 |
| spacer_ring | DIN 988 | ✅ 精确DIN 988表 (thin shim) 2026-04-18 |
| snap_clip | DIN 6799 | ✅ 完全重写为E型卡圈 2026-04-18 |
| hex_standoff | ISO 272 | ✅ standard属性已修正为ISO 272 2026-04-18 |

Tier 2 — 部分标准化（关键参数表驱动，比例公式）：
| Family | 标准 | 状态 |
|--------|------|------|
| spur_gear | ISO 53 | ✅ 已用ISO 54 module系列 |
| helical_gear | ISO 53 | ✅ 同spur_gear module |
| bevel_gear | ISO 23509 | ✅ ISO 54 module + DIN 6885A keyway table 2026-04-18 |
| worm_screw | ISO 10828 | ✅ 已加preferred q系列 2026-04-18 |
| sprocket | ISO 606 | ✅ 已用ISO 606 pitch/roller表 |
| pulley | ISO 22 | ✅ ISO 22 groove angles + ISO 4183 belt table 2026-04-18 |
| hollow_tube | EN 10219/10305 | ✅ 已有精确EN 10219 SHS/RHS表 |
| knob | DIN 319 | ✅ 已加DIN 319表 2026-04-18 |
| ball_knob | DIN 319 | ✅ 已加DIN 319球形表 2026-04-18 |
| hinge | DIN 7954/7955 | ✅ 已加DIN 7954表 2026-04-18 |
| pipe_elbow | ASME B16.9 | ✅ 已加ASME B36.10M NPS表 2026-04-18 |
| t_slot_rail | DIN 650 | ✅ 已用ISO 299 T-slot表 |
| mounting_angle / l_bracket | EN 10056 | ✅ 已加EN 10056表 2026-04-18 |
| rect_frame | N/A (custom machined) | ✅ standard corrected to N/A; preferred-size table added 2026-04-18 |

---

### UA-5 — ISO 标准化全量 family + standard 列 🔴 HIGH (2026-04-18)

**目标：**
1. 为每个 family 找对应 ISO/DIN/ASME 标准，用表格驱动 `sample_params`
2. `synth_parts.csv` 加 `standard` 列（e.g. `"DIN 950"`, `"ISO 4032"`, `"N/A"`）
3. QA 已在 meta.json 里（`qa_generator.py`），无需加列

**实现方式：**
- `BaseFamily.standard = "N/A"` 类属性
- 各 family 子类设置 `standard = "DIN 950"` 等
- `exporter.py` `SYNTH_FIELDS` + CSV row 加 `standard`

**进度：**

| Family | 标准 | 状态 |
|--------|------|------|
| handwheel | DIN 950 | ✅ 表格驱动 DONE 2026-04-18 |
| spur_gear | ISO 53 | ✅ standard set 2026-04-18 |
| helical_gear | ISO 53 | ✅ standard set 2026-04-18 |
| bevel_gear | ISO 23509 | ✅ standard set 2026-04-18 |
| hex_bolt | ISO 4014 | ✅ standard set 2026-04-18 |
| hex_nut | ISO 4032 | ✅ standard set 2026-04-18 |
| plain_washer | ISO 7089 | ✅ standard set 2026-04-18 |
| circlip | DIN 471/472 | ✅ standard set 2026-04-18 |
| sprocket | ISO 606 | ✅ standard set; ⚠️ params may not be fully table-driven |
| knob / ball_knob | DIN 319 | ✅ standard set 2026-04-18 |
| spacer_ring | DIN 988 | ✅ standard set 2026-04-18 |
| snap_clip | DIN 6799 | ✅ standard set 2026-04-18 |
| hinge | DIN 7954/7955 | ✅ standard set 2026-04-18 |
| pipe_elbow | ASME B16.9 | ✅ standard set 2026-04-18 |
| threaded_adapter | ASME B1.20.1 | ✅ standard set 2026-04-18 |
| mounting_angle / l_bracket | EN 10056 | ✅ standard set 2026-04-18 |
| rect_frame | EN 10219 | ✅ standard set 2026-04-18 |
| t_slot_rail | DIN 650 | ✅ standard set 2026-04-18 |
| shaft_collar | DIN 705 | ✅ standard set 2026-04-18 |
| hex_standoff | DIN 7984 | ✅ standard set 2026-04-18 |
| dowel_pin | ISO 8734 | ✅ standard set 2026-04-18 |
| parallel_key | DIN 6885 | ✅ standard set 2026-04-18 |
| taper_pin | ISO 2339 | ✅ standard set 2026-04-18 |
| pulley | ISO 22 | ✅ standard set 2026-04-18 |
| hollow_tube | EN 10305 | ✅ standard set 2026-04-18 |
| worm_screw | ISO 10828 | ✅ standard set 2026-04-18 |

---

---

## UA-7 — 标准化 Tier C Family 修复 🔴 HIGH (2026-04-18)

**目标：** 8 个有标准但参数化不符标准的 family，按优先级逐个修复，改为表驱动。

### 子任务列表

| # | Family | 标准 | 核心问题 | 状态 |
|---|--------|------|----------|------|
| UA-7-1 | threaded_adapter | ASME B1.20.1 | 0个表，14个uniform，完全没实现标准 | ✅ DONE 2026-04-18 |
| UA-7-2 | spur_gear | ISO 53 | z用uniform，keyway比例凭空，face_w全uniform | ✅ DONE 2026-04-18 |
| UA-7-3 | helical_gear | ISO 53 | 同spur_gear + helix_angle全uniform | ✅ DONE 2026-04-18 |
| UA-7-4 | bevel_gear | ISO 23509 | pitch_angle uniform，keyway比例凭空 | ✅ DONE 2026-04-18 |
| UA-7-5 | pulley | ISO 22 | 几乎全uniform，只有belt groove从表 | ✅ DONE 2026-04-18 |
| UA-7-6 | sprocket | ISO 606 | disc_thickness/bore_d uniform，keyway凭空 | ✅ DONE 2026-04-18 |
| UA-7-7 | t_slot_rail | DIN 650 | slot_depth/back_w/wall_t均为uniform | ✅ DONE 2026-04-18 |
| UA-7-8 | hex_standoff | ISO 272 | flange_od/bore_step为uniform | ✅ DONE 2026-04-18 |

### 各任务改进方案

**UA-7-1 threaded_adapter (ASME B1.20.1):**
- 加 ASME B1.20.1 NPT 尺寸表：NPS 1/8–2"，含 hex AF、stub OD、thread pitch
- 从表采样替代所有 hex/stub uniform 调用

**UA-7-2 spur_gear (ISO 53):**
- `z = rng.integers(14, 36)` (不是 uniform)
- `face_w = rng.choice([6,8,10,12]) * m`
- `bore_d` → DIN 6885A 反查合理范围
- keyway → `din6885a_keyway(bore_d)`

**UA-7-3 helical_gear (ISO 53):**
- 同 spur_gear 所有修改
- `helix_angle = rng.choice([15, 20, 23, 25, 30])`

**UA-7-4 bevel_gear (ISO 23509):**
- `pitch_angle = rng.choice([15,20,25,30,35,40,45])`
- bore_d 合理范围；keyway → `din6885a_keyway(bore_d)`

**UA-7-5 pulley (ISO 22 + ISO 4183):**
- 以 ISO 4183 belt 型号为锚点
- belt 定 groove_w → rim_r 从表选 → hub/spoke 按比例
- bore_d → DIN 6885A

**UA-7-6 sprocket (ISO 606):**
- `disc_thickness = rng.choice([0.8,0.9,1.0,1.1,1.2]) * dr`
- bore_d → DIN 6885A 范围；keyway → `din6885a_keyway(bore_d)`

**UA-7-7 t_slot_rail (DIN 650):**
- slot_depth/slot_back_w/wall_t 改为从 DIN 650 标准 profile 比例表取

**UA-7-8 hex_standoff (ISO 272):**
- `flange_od = af * rng.choice([1.4,1.5,1.6,1.8])`

---

## UA-8 — Docstring 标准来源链接 🔴 HIGH (2026-04-18)

**目标：** 每个有具体标准的 family (33个)，在 docstring 里加参数示意图和表格的来源链接。
格式：`Reference: <标准名> — <链接或文档标题>`

**进度：**

| Family | 标准 | 状态 |
|--------|------|------|
| all 33 families | various | ✅ DONE 2026-04-18 |

---

## 已完成

| Task | 完成时间 | 说明 |
|------|---------|------|
| UA-2 t_pipe_fitting 装配顺序 | 2026-04-17 | branch cut → main bore cut 顺序正确 |
| UA-3 handwheel DIN 950 修复 | 2026-04-18 | centered cylinder offsets, validate_params, handle |
| t_pipe_fitting visual 验证 | 2026-04-18 | 与 manual 对比 OK |
| UA-5 standard 列 + 28 families | 2026-04-18 | BaseFamily.standard + exporter standard column; 28 families set |
| UA-6 ISO 标准化 family 脚本 | 2026-04-18 | 15+ families rewritten with exact ISO/DIN tables; rect_frame→N/A |

---

## Bug Fix Queue

| Bug | 优先级 | 状态 |
|-----|--------|------|
| spur_gear/helical_gear annular web recess 验证 | ⭐ HIGH | ✅ 100% build pass 2026-04-18 |
| spur_gear rim_boss 配套 hub_boss | ⭐ HIGH | ✅ 100% build pass 2026-04-18 |
| sprocket keyway DIN 6885A | 🟡 MED | ✅ 已修 2026-04-18 |
| bearing_retainer_cap ear bolt hole 圆角 | 🟢 LOW | 待下批次 |

---

## Pending 渲染验证

- `propeller` ✅ build pass (easy/medium/hard) 2026-04-18 — 视觉验证待 Synth Monitor
- `manifold_block` ✅ build pass (easy/medium/hard) 2026-04-18 — 视觉验证待 Synth Monitor
- `lathe_turned_part` ✅ build pass (easy/medium/hard) 2026-04-18 — 视觉验证待 Synth Monitor
