
## 2026-04-27 (session 30) — UA-25 cad_curated_722 → v2 (720 rows, OCC 验证, HF 推 `Hula0401/cad_curated_722_v2`) ✅

- 起因:`qixiaoqi/cad_curated_722` 是 bench 最终评测集,5 个 substitution-target family 需 gt_code 手改 (`cable_routing_panel` / `clevis` / `parallel_key` / `tapered_boss` / `z_bracket`)
- **新建 `cq_gui/`** sandbox (gitignore):py3.11 + cadquery 2.7 + cq-editor 0.7 隔离 venv,本 repo cq 2.3 不动
  - `cq_gui/launch.sh` → CQ-editor 启动;`cq_gui/scratch.py` 起手 demo
  - `cq_gui/curated_722/<family>/<idx>__<stem>.py` × 722 dump (META sentinel 隔离 + gt_code body 可改),`_INDEX.md` 索引,`_original.parquet` 冻结源
  - `cq_gui/sync_back.py` → 扫 .py → diff vs `_original.parquet` → 写新 parquet
- **手改 20 行 + 删 2 行**: 5 高亮 family 内 gt_code 修(loft circle 顺序、hole 偏移、slot 尺寸等);clevis #10 #11 (`synth_clevis_000074/000177`) 因 geometry 不合理 drop
- **OCC 全量校验** (`cq_gui/exec_check.py`):cadquery 2.7 exec gt_code → bbox + volume → **719/720 pass (99.86%)**, 1 fail = `synth_double_simplex_sprocket_000579_s4420` (hard, 20s timeout);median 0.088s · p95 0.467s
- **重 render 20 个改过的 case** (`cq_gui/rerender_edited.py`):exec → STEP export → `render_normalized_views.render_step_normalized` 4-view composite,与 v1 同 cadrille style
- **HF push** `Hula0401/cad_curated_722_v2`(720 rows · 14.4MB · `+exec_ok` `+exec_reason` `+exec_dt_s` 三列 · README diff 写明)
- **Discord** 发分布长图 6 段 chunk (3426×33596 单图 15MB 超 webhook → 切 6 段) + v2 chunk 1 重画(`EDIT` blue + `OK`/`FAIL` badge,只 chunk 1 含改动,2-6 沿用 v1)
- **artifacts**:`cq_gui/curated_722/{curated_722_v2.parquet, exec_report.json, _v2_chunk1.png, _rerendered/*.png}`、`tmp/cad_curated_722/{cad_curated_722_gallery.png, chunk_01-06.png}`
- 一个坑:cq-editor pip 装 default Python 3.14 没 PyQt5 wheel → 隔离 venv 钉 3.11

## 2026-04-27 (session 29) — UA-24 106 simple_* family + 7655 rows → HF `cad_bench_simple106` ✅

- **registry 最终 106 个 simple_*** = 21 part-style + 85 across 5 packs (profiles/cylindrical/blocks/multi_stage/sheet_sections)。Pack 文件:`scripts/data_generation/cad_synth/families/simple_{profiles,cylindrical,blocks,multi_stage,sheet_sections}_pack.py`
- **第 1 阶段 21 个 simple_<part>** (替复杂 parent 简化 + DeepCAD/F360 启发独特):
  spur_gear / helical_gear / bevel_gear / sprocket / double_sprocket / impeller / propeller /
  bellows / coil_spring / torsion_spring / twisted_drill / pulley / spline_hub / worm_screw +
  plate_holes_grid / step_solid / l_solid / t_solid / curved_lobe_plate / open_box_thin / multi_extrude_step
- **第 2 阶段 85 个 pack family** (来自 F360/DeepCAD 视检 138+53 样本归类的 16 类 shape):
  - **profiles_pack 30**: trapezoid/parallelogram/wedge/diamond/chevron/cross/arrow/house/pentagon/hexagon/heptagon/octagon/n_star/keyhole/stadium/half_disc/pie_slice/quarter_disc/crescent/dogbone/h_section/z_section/y_shape/corrugated/serrated/d_shape/annulus/rounded_rect/capsule/slot_through (`_PolyFamily` 基类,sketch-first 单 polyline → close → extrude,`ALLOW_FEATURES = False` 防 BRep)
  - **cylindrical_pack 15**: frustum_cone/d_shaft/double_d_shaft/grooved_shaft/radial_holes_tube/axial_slot_cylinder/chamfer_shaft/stepped_shaft_basic/hollow_pipe/thin_disc/thick_ring/hemisphere/tapered_pin/capsule_3d/grooved_disc
  - **blocks_pack 15**: chamfered/filleted/pyramid/obelisk/pocket/through_slot/round_hole/oval_hole/keyway/cross_cut/array_holes/chamfered_corners/dovetail/v_block/round_pocket
  - **multi_stage_pack 12**: disc_with_boss/pegs/skirt/holes_polar/plate_with_pegs/button/funnel/handle_block/two_step_cylinder/block_with_studs/lid_flange/axle_yoke
  - **sheet_sections_pack 13**: c_channel/u_channel_simple/hat_section/z_section_struct/i_beam_simple/angle_bracket_90/angle_bracket_135/box_section/unistrut/top_hat_section/l_section_thin/split_tube/bent_strip
- **REF 来源**: 每 family 带 `REF` 属性 — F360 stem (`f360:<stem>`) 或 imagined rationale。预览 gallery 把 ref 放最左 (F360 红框,imagined 文字卡)
- **数据生成**:
  - batch_simple21_apr27 (seed=4127, 4200 → **3473 verified, 82.7%**)
  - batch_simple85_apr27 (seed=4128, 4250 → **4182 verified, 98.4%**) — 最高 100% (hat_section/oval_hole/top_hat/obelisk/serrated), 最低 28% (split_tube)
- **HF push**: `BenchCAD/cad_bench_simple106` 单 test split, **7655 rows** (3473+4182), 160MB parquet, `source_run` 字段标 batch 来源 → https://huggingface.co/datasets/BenchCAD/cad_bench_simple106 (与现有 `cad_bench` 完全独立,不覆盖 20143 行)
- **预览 gallery**: `tmp/simple106_previews/GALLERY_simple106.png` (2400×44472, 12MB) + 102 单 family strip,layout = [REF | s1 | s2 | s3 | s4 | s5]
- **F360/DeepCAD 数据落盘**: F360 r1.0.1 reconstruction (8626 jsons, 2.1GB) + DeepCAD data.tar (208MB) → `data/data_generation/open_source/`
- **视觉分类**: F360 138 + DeepCAD 53 = 191 张人工分 16 类 (trapezoid 18%, parallelogram 11%, frustum 9%, polygon block / wedge / ring / crescent / cross / half-disc / diamond / concave polygon / multi-piece / corrugated / pie slice / keyhole / sheet section)
- **Discord webhook integration**: `scripts/data_generation/discord_progress.py` 读 `DISCORD_WEBHOOK_URL` (`.zshrc` 全局变量),`discord_status_loop.sh` 5 min 间隔 post (batch + render + family-pack 计数器),所有里程碑实时通知
- **修复记录**:
  - simple_propeller polyline coincident pts → BRep failure → consecutive-point dedupe + twistExtrude angle=0 ZeroDivisionError → 过滤 [15,20,25,35,45]
  - simple_impeller petal_outline 复用 dedupe
  - simple_l_solid l_filleted fillet 半径过大 → `min(t * 0.3, 1.5)`
  - simple_sprocket hub_d ≥ radius INVALID → clamped `min(bore * uniform, r * 0.85)`
  - simple_worm_screw flat_helix_cut Null TopoDS → 替换为 `shaft_two_steps`
  - blocks_pack cross_cut/dovetail/v_block/round_pocket validate 过紧 → 改 L/W/H 比例 clamp
  - DeepCAD render 米单位 → `SCALE = 1000.0` 修
- **CLAUDE.md** 更新 family registry source-of-truth note (count 106, 不引用过时 docstring)

## 2026-04-25 (session 28) — bench 一键 fetch + UI 直读 from_hf

- 新 `bench/fetch_data.py`:一行 `uv run python bench/fetch_data.py` 拉两个 HF repo (`BenchCAD/cad_bench` 20143 + `BenchCAD/cad_bench_edit` 336) 入 `~/.cache/huggingface`,顺手把 edit bench 解包到 `data/data_generation/bench_edit/from_hf/` (records.jsonl + orig_steps/ + gt_steps/ + orig_codes/ + gt_codes/, ~124MB)
- UI `EDIT_SOURCES` 加 `"from_hf"` (`scripts/data_generation/ui/app.py:1108-1112`):fresh clone 起 streamlit 直接选数据源 from_hf 就能看 — 不用先跑 curation 链
- HF cad_bench_edit 实际 schema 只有 `record_id/family/edit_type/difficulty/instruction/iou/source/orig_code/gt_code/orig_step/gt_step` (README 写的 `iou_orig_gt`/`level`/`axis`/etc 早过时);UI 通过 `_eb_iou` fallback 自洽,但 dump 字段按真实 schema 取
- 顶层 README + bench/README 加快速启动 step
- argparse 风格、ROOT/sys.path/load_dotenv 顶部样板对齐 `bench/eval.py`,走 `bench.dataloader.load_hf` 复用现有 wrapper
- Smoke:`fetch_data.py` 实跑 OK,records.jsonl 336 行 iou 全填,UI 数据源切 from_hf 路径连通;black/ruff(新文件 0 err)/pytest 81 pass

## 2026-04-24 (session 28b) — NeurIPS 2026 D&B 投稿启动 + 7 篇 reference digest

- 下 NeurIPS 2026 LaTeX 模板到 `paper/neurips_2026/`(`neurips_2026.{tex,sty}` + `checklist.tex`);E&D track 用 `\usepackage[eandd]{neurips_2026}`(默认双盲,可加 `nonanonymous` 切单盲);9 页正文上限,refs/appendix/checklist 不计;abstract 5/4 截、全文 5/6 截 AoE
- 写 intro 第一稿到 `paper/draft_intro.md`(750 字,5 段 + 5 contribution),把 CVPR 旧稿的 *curation pipeline* framing 改成 *dataset + benchmark* 框架
- 下 7 篇 reference PDF 到 `paper/references/`:
  - CAD 直接竞品 4 篇:Text2CAD (NeurIPS'24 D&B)、CAD-Coder (NeurIPS'25 main)、CAD-Recode (ICCV'25)、CADCodeVerify/CADPrompt (ICLR'25)
  - D&B 结构标杆 3 篇:Infinity-Chat (NeurIPS'25 best D&B)、MMSI-Bench (ICLR'26)、AutoCodeBench (ICLR'26)
- 4 个并行 agent 分工读 + 写 7 个 `paper/references/notes/<slug>.md` 结构化分析(storyline / claim 链条 / 关键数字 / 对 Cadance 启发 / 一句话定位)
- 综合写 `paper/references/SUMMARY.md`:跨篇 storyline DNA、表/图 layout 标杆、metric 对比、4 个 CAD 竞品逐一定位、6 条审稿人会问 + 答案模板、intro 更新 checklist
- 关键发现:(a) 三件套 contribution(real data + taxonomy + dense GT)是 D&B 通用骨架;(b) sticky term 命名(Hivemind / scaling cliff)是 sell finding 的标配;(c) AutoCodeBench 的 Lite/Complete 子集设计强烈建议借鉴;(d) CADCodeVerify 200 例 + 无 family + bbox IoU 是其结构性弱点,我们 20K + 106 family + rotation-inv IoU 直接打;(e) human/expert upper bound + scaling cliff 实验是 reviewer hard requirement,Cadance 还缺,需补

## 2026-04-23 (session 27) — UA-23 apr20-20k 全清 + HF 重推 + 本地↔HF align

- hollow_tube YZ/XZ base_plane 下 box+rect 切成两块板（33 apr20 sample），family op 序列只适配 XY → 直接删样本 + 家族 standard 字段 `EN 10305 → EN 10219`（尺寸表本来就是 EN 10219，346 行回填）
- `exporter._next_gid()` race condition 造 985 个 duplicate gid：这次 renumber 1..N 抹平；根治（flock/SQLite）留下一任务
- 发现 `exporter.py:87` `gt.step = gen.step` 让 IoU 校验永远 1.0 自通过（hollow_tube 多 solid 才进了 verified）；没动，下一任务
- 新增 **sticky exec-cache 3 列**到 `synth_parts.csv`：`code_exec_ok` / `code_exec_reason` / `code_exec_checked_at`（写入 `exporter.SYNTH_FIELDS`；HF push 不 leak，因 push_bench_hf 从 meta.json 构 row 不读 CSV 列）
- `_upload_filter.revalidate_exec` 改 cache-aware：load CSV → skip True / 取 False 不 rerun / 只 exec 未检过；增量 checkpoint `tmp/exec_cache_checkpoint.jsonl`（每 2000）防崩丢
- 第一轮 `_write_exec_cache` 踩 pandas `LossySetitemError`（float64 列 setitem 字符串），40 min exec 结果丢光；改成 map-based 向量化 + `.fillna().astype(str)` 先拉成 object dtype 再写入
- 全量 exec 校验 20221 apr20 accepted：**20143 pass / 78 fail (0.39%)**；fail 扎堆 `double_simplex_sprocket` 50 例，`Standard_Failure` 69 / `exec_timeout` 5 / `zero_volume` 4
- 删 78 fail + rm stem 目录 + renumber gid → CSV 36098 行
- 清 apr20 rejected 2920 行（没磁盘 artifact，纯 CSV bookkeeping）
- `HfApi.delete_repo(BenchCAD/cad_bench)` 重推,cache 全命中秒过 exec，只耗 parquet 上传
- **align 核对：HF test split = 20143，local (accepted apr20 ∩ exec_ok=True) = 20143，stem set 双向 diff = 0**
- 3 份 CSV 备份 `.bak_ua23_*`(pre-clean / pre-addcols / pre-purge)
- 余问题:78 fail 的 `double_simplex_sprocket` 批量 `Standard_Failure` 需定向查（fillet/chamfer 系列几何异常);`gt.step = gen.step` 复制 + `gid` race condition 两个根因 pipeline 未修

## 2026-04-22 (session 26) — edit bench singleton 填补 + count-change 任务

- 审 pairs_curated.jsonl：4 family 只 1 data point（L1+L2 算 1）→ capsule/turnbuckle/circlip/twisted_bracket
- 新 `tmp/build_topup_edits.py`：6 条 add/remove edit via string-replace gt_builder + 每 edit per-edit orig regeneration（避免 stale STEP）
  - turnbuckle add_chamfer 2.0mm 在 `|X` long outer edges（iou=0.9705）
  - circlip add_chamfer 0.4mm 在 `>Z` top edges（iou=0.9898）
  - table remove_leg 4→3（删 `(-93.75,-57.6,-78.25)` 腿，iou=0.9046；user 举例的 count-change）
  - hex_standoff add_chamfer 0.5mm 在 top hex rim（iou=0.9936）
  - tapered_boss add_hole 12.0mm 中心 bore（iou=0.9515）
  - pan_head_screw add_chamfer 0.4mm 在 head 顶（iou=0.9805）
- 踩坑：twisted_bracket 移孔 iou=1.0（体素 64³ 看不见 2.5mm 半径孔）+ dome_cap revolve+arc STEP 导出丢弧段（ylen 91.6→31.4）→ 两者 drop
- twisted_bracket 改 `curate_supplementary_plan.json` dim 补位：plate_width 16→20 (+25%)，iou=0.7749
- `curate_finalize.emit_additive_records` 支持 `remove_*` op_type：rid 直接用 `{family}_{op_type}_L1`，orig_value 从 plan entry 读，unit 默认 count（remove）/mm（add）
- 最终 **433 records**：212 dim + 58 dim-supp(29×2) + 45 add(39+6) + 118 multi；106 families；1 singleton 剩 capsule（球面 tessellation iou metric bug，session 22 已记录）
- 分布：77 family 2dp, 28 family 3dp, 1 family 1dp

## 2026-04-22 (session 25) — UA-22 bench runner 通用化

- 6 runner 重构成 plug-and-play model + 固定 `results/<task>/<model>/` 分任务落地 + dedup + 可复现 stratified 采样
- 新增：`bench/models/registry.py` (ModelAdapter ABC + register/get_adapter), `providers/{openai,local_hf}.py`, `prompts.py` (集中所有 SYSTEM/USER 提示词 + parse_qa_answers), `bench/sampling.py` (n>200 自动 stratified, 每 family ≥1), `bench/results.py` (ResultsDir 管理 append-only pool + sidecar runs/)
- 重命名：`eval_qa.py → eval_qa_img.py`, `run_edit.py → run_edit_code.py`, `run_edit_vlm.py → run_edit_img.py` (统一 `qa_img / qa_code / edit_img / edit_code` 命名)
- 6 runner main 全部瘦身：`--model` required（去 default `gpt-4o`），去 `--out` / `--resume` / `--per-family`，统一 `--limit --seed --split --repo`
- `bench/models/__init__.py` 留 5 个 back-compat shim (call_vlm/call_vlm_qa/call_llm_qa_code/call_edit_vlm/call_edit_code)，旧 import 不炸
- Smoke：3 model (gpt-4o-mini / gpt-4o / gpt-4.1-mini) × 2 task (qa_img / qa_code) × N=3 seed=42 → ✅ 同 seed 3 stem 跨 model/task 完全一致；N=3→N=5 同 seed 自动跳过 done=3 todo=2；4 (task,model) 子目录互不污染
- `pytest 83 pass`, `ruff` 我新加文件 0 error

## 2026-04-22 (session 24) — edit bench add_* 指令自查

- 审 41 个 add_* case：发现 2 个 broken（orig 是裸 box，GT 多 8-11 个操作）、4 个多孔说"a hole"、6 个 pattern 无位置/数量、1 个面搞反、2 个边选符错、2 个 "outer edges" 模糊
- Fix：
  - 删 `pipe_flange_add_chamfer` + `slotted_plate_add_chamfer`
  - 改写 10 多孔指令（clevis "两孔一臂一个"、flat_link "两端"、manifold_block "三孔沿长轴"、mounting_angle "三孔沿腹板"、cruciform "四臂端"、dog_bone "两 lobe"、ratchet_sector "沿弧"、mounting_plate/sheet_metal_tray/locator_block "四角"）
  - 16 单孔加 "through"（.hole() 默认即 through-all）
  - 边选符：dowel_pin "top + bottom"、wing_nut "wing edges"、bucket "top rim"、parallel_key "long edges"
  - `sheet_metal_tray` face 错：top→bottom（GT 确实 `<Z`）
- 只改 `curate_additive_plan.json` + 跑 `curate_finalize.py`：41→39 additive records，总 371→369
- Re-audit 0 mismatch

## 2026-04-22 (session 23) — pulley pocket cap + 20k dataset fix

- Bug：pulley hard 的 spoke pocket 对大 pulley 失控（rr=250 pl=119.5 pt=105.7），占满 radial web
- Fix `pulley.py:243-258`：pocket_tang 上限 0.4·rr、pocket_l 上限 0.25·rr（用户 ref rr=45→pl=13.5/pt=22.62 ratio 的 ~80%，避免破坏结构）
- 188 hard sample 0 violation、30 roundtrip exec 0 fail
- 20k dataset 更新踩坑：`--resume` 因其他 family 近期改过 (clevis_pin/hex_standoff/hinge/knob/...)  → RNG drift → sample#2 起 stem 名完全不同 → 37 min 白跑 1452 新样本（4 个恰好命中 hard pulley）
- 清理：1177 与 OLD 同 fam+diff+params 的重复 stem 删除、275 unique-new（含 6 pulley）保留、85 空壳 hard pulley dir（参数已丢）删除
- 重跑走独立 `batch_pulley_hard_apr22.yaml` (pulley-only, seed=4423, 100 hard, run_name 复用 batch_20k_apr20) → 100/100 accepted ~5 min，0 cap violation
- 最终 pulley in batch_20k_apr20：80 easy + 69 medium + 104 hard（原 85 hard 替换为 100 新 hard）
- 教训：跨 family 改过代码后 `--resume` 不再可靠；family-scoped topup 要单跑 config

## 2026-04-22 (session 22) — UA-20 curated edit bench

- 问题：724 pairs 有高耦合 edit（knob total_height → 33 处 magic number 联动），模型不可能答对
- 两阶段 curate：新 body-line single-value edit + 现有 pairs.jsonl 低-dl 筛选
- 新 `bench/edit_gen/curate_pairs.py`：对每 family 选一个 param（late-feature 优先 fillet/chamfer/bore），单值 regex 替换 + exec gt + IoU
- 新 `bench/edit_gen/curate_preview.py`：side-by-side orig|gt 四视图 caption 预览
- 新 `bench/edit_gen/curate_finalize.py`：`curate_final_plan.json` → `pairs_curated.jsonl`（L1+L2）
- 过滤：drop capsule/rivet (tessellation iou=0), drop twisted_bracket (dl=20)，flat_link 改 cc_distance (iou=0.86)
- 结果：101 families、--exclude-hard=89 families=178 records, dl∈[2,6] median=4, iou∈[0.58,0.99] median=0.94
- 分布：length 23% / radius 14% / other-dim 15% / hole 12% / height 8% / diameter 8% / width 6% / fillet-chamfer 5% / thickness 5% / angle 2% / depth 2% / slot 1%
- Preview: `data/data_generation/bench_edit/previews/<family>.png`
- pulley root 换 gid=10233 synth (bore_radius 内孔 normalize 洗掉 → 改 rim_radius +3% iou=0.961)
- 扩充 additive (add_hole/chamfer/fillet) + multi-param (2 axes)：
  - `curate_additive_plan.json` 12 条：2 add_chamfer + 1 add_fillet + 9 add_hole；subprocess preamble 加 HashCode shim + 绝对 step path + smart strip (walk back 过 SELECTOR op 到 CONSTRUCT op)
  - 迭代放大 target：drop iou>=0.999 的 8 条 (hole/fillet 太小 → 64³ 体素看不见)；handwheel chamfer 3.2→8 / locator_block hole 4→14 / manifold_block hole 5.5→18 / wing_nut fillet 0.6→2.0 / pipe_flange chamfer 放大后 geometry 炸 → drop
  - `curate_multi_plan.json` 28 条 (2 param × 2 lvl)：dim 13 (旧) + 15 新 (8-15% pct 确保 iou<0.99)：ball_knob/hex_nut/knob/washer/round_flange/enclosure/hinge/battery_holder/fan_shroud/hex_key_organizer/keyhole_plate/connecting_rod/heat_sink/threaded_adapter/gusseted_bracket
  - 旧 cable_routing_panel/eyebolt 重 multi 用 10-12% pct 把 iou 从 0.997 降到 0.98
  - `curate_finalize.py` 重写支持 3 plan；`curate_preview.py` 泛化 title + 多 plan source
- 最终 **248 records**：180 dim(L1+L2) + 12 add(L1) + 56 multi(L1+L2)；iou min=0.574 median=0.934 max=0.9899 (全部 <0.99)；95 unique family
- Contact sheet: `data/data_generation/bench_edit/previews/_contact_enriched.png`
- 补齐 4 孤儿 family（user 要求覆盖全 106）：
  - worm_screw（orphan_fill, shaft_length +15% iou=0.573）
  - twisted_bracket（orphan_fill, plate_length +15% iou=0.959）
  - sprocket（orphan_gen, 重 sample seed=42 + disc_thickness +20% iou=0.979）
  - capsule（orphan_reseed, seed=0 radius +10% iou=0.922）
  - rivet（orphan_reseed, medium diff seed=10 shank_length +15% iou=0.943；easy 版 sphere_radius 导致 tessellation 失败，换 medium 带 tip_chamfer）
- 再跑 finalize 不加 `--exclude-hard`（dim plan 全 iou<0.99，11 family dl>6 全保留）
- **280 records**：212 dim(L1+L2) + 12 add(L1) + 56 multi(L1+L2)；iou min=0.573 med=0.935 max=0.9899 (0 violation)；**106 unique family**；dl mean=4.3 max=14
- 扩 additive 12→41 / multi 28→59：v3/v4/v5 多轮尝试（strip-tail-op 失败的小特征改用 inject-big-hole 方案）
  - additive drop 条件：iou≥0.99（小 chamfer/hole 在 64³ 体素下隐形）
  - multi v4 用 `inspect_params.py` 提取 body 真实参数名（替换 v3 猜测的 derived 参数）
  - 新家族 additive 覆盖：dowel_pin/parallel_key/pipe_flange/propeller/ratchet_sector/sheet_metal_tray/chair/mesh_panel/keyhole_plate/heat_sink
  - 新家族 multi 覆盖：bearing_retainer_cap/cam/connector_faceplate/dovetail_slide/duct_elbow/grommet/hollow_tube/l_bracket/motor_end_cap/pillow_block/pipe_flange/shaft_collar/slotted_plate/stepped_shaft/t_pipe_fitting/z_bracket/helical_gear/pcb_standoff_plate/propeller/piston/ratchet_sector/sheet_metal_tray/star_blank/worm_screw/vented_panel/waffle_plate
- **最终 371 records**：212 dim(L1+L2) + 41 add(L1) + 118 multi(L1+L2)；iou min=0.031 med=0.93 max=0.9899 (0 violation)；106 families；previews 213 张

## 2026-04-21 (session 21) — silent-hole 检测 + hex_standoff 重写

- user call-out：37619 hex_standoff flange 太宽；37520/37554 taper_pin hole>pin；washer 需要 fillet
- hex_standoff 重写（ISO272 tap-drill 表）：easy=通孔；medium=hex+stud+盲孔（tap-drill）；hard +stud_chamfer。3000 样 pass
- plain_washer：medium 单面 fillet, hard 双面。3000 样 pass
- taper_pin hard：extraction_thread_m 只在 `m*0.85 < d_nom*0.55` 时加
- 新检测 `tmp/_audit_hole_shrink.py`：每个 hole op 把 diameter 换成 0.1mm 重 build，比较 solid volume，drop > thresh 就疑似
- 审计 23,323 accepted stems × per-family median+IQR outlier：49 taper_pin stems (hole=2.55 于 d_nom<5) 是 bug → `status=rejected reject_stage=audit_oversize_hole`
- 其他 high-drop family (standoff/washer/spacer_ring/pipe_flange/flat_link/dog_bone/cruciform/round_flange) 均 design-intent 大孔，非 bug
- propeller 2 stems drop=46% (blade-root 与 bore 相交)，非 oversize 孔，不动
- hex_standoff 9 样 grid: `tmp/hex_standoff_preview_apr21/grid_9.png`（新几何；UI 未 rebatch 所以仍显示 flange 版本）

## 2026-04-21 (session 20) — 20k gt_code 对齐修复

- 根因：`_apply_op` 对 chamfer/fillet 静默 try/except → wp 建成功但 render 出的 gt_code 再 exec 必炸 → code/geo/render 不对齐
- `pipeline/builder.py` 去掉 chamfer/fillet silent-swallow；`pipeline/validator.py` 新增 `validate_roundtrip` (Stage F2 post-filter，render→exec→face count 比对)
- 18 家族源码修复：
  - 显式 drop：knob、washer、hinge (fillet/chamfer 无标准要求) + bearing_retainer_cap (boss_chamfer) + hex_standoff (fillet)
  - 重排：hex_standoff 把 chamfer 放在 stepped bore 之前；hinge 把 screw hole 放在 knuckle union 之前（`>Z` 单面）
  - clevis_pin `|Z` → `>Z or <Z`；spline_hub drop chamfer；taper_pin 改 `>Y`
  - 其余家族靠 silent-swallow 去除后 + roundtrip post-filter 自动修（handwheel、hex_nut、taper_pin、standoff、u_channel、spline_hub、mounting_plate、rib_plate、sprocket、threaded_adapter、lathe_turned_part）
  - worm_screw 虚惊（subprocess STEP export 超时，in-process 30/30 OK）
- 验证：全 18 家族 in-process roundtrip 30/30 pass（除 handwheel 25/25+5bf，mounting_plate 28/28+2bf，build fail 被 post-filter 拦截不入数据）
- Replacement batch_fix_18fam_apr21：3600→3359 accepted (93.3%)；post-filter reject 241（112 build_fail + 100+ roundtrip_face_mismatch + 37 worker）
- 全量审计 old batch_20k_apr20 18fam 3611 accepted → 1552 bad (43%)：clevis_pin 225/225、spline_hub 182/182 全炸；rejected 进 synth_parts.csv + 目录挪到 `tmp/trash_bad_apr21/`（可恢复）；`synth_parts.csv.bak_apr21` 备份
- 最终 20k 等价数据 = 19964 good old + 3359 new = 23,323 aligned stems



- 新 `bench/edit_gen/upload_edit_hf.py`：读 `pairs.jsonl` + codes/ + steps/，每行 embed `orig_code`/`gt_code` 文本 + `orig_step`/`gt_step` bytes + params/instruction/iou
- 推到 `Hula0401/cad_synth_bench_edit` split=`test_iid`：724 rows, 104 families, L1×362+L2×362, 56MB parquet
- gitignore 加 `website/`

## 2026-04-20 (session 18) — UA-21 code→QA bench runner

- 新 `bench/eval_qa_code.py`：纯文本 LLM 从 `gt_code` 读 CadQuery，回答 `qa_pairs` 问题，复用 `qa_score`
- `bench/models/__init__.py` 新增 `QA_CODE_SYSTEM_PROMPT` + `call_openai_qa_code` + `call_llm_qa_code`（文本 API，`max_tokens` / `max_completion_tokens` 按 gpt-5.x 区分）
- HF 数据复用既有 `Hula0401/cad_synth_bench_smoke`（`gt_code` + `qa_pairs` 都已 embedded）
- E2E: GPT-4o 12 samples parse 12/12, qa_score 0.526; bolt 1.000 / ball_knob 0.854 / clevis_pin 0.250 / bevel_gear 0.000
- README +3rd bench section；TASK_QUEUE UA-21 DONE

## 2026-04-20 (session 17) — UA-19 Edit benchmark 数据生成

- 新 `bench/edit_gen/` 包：`edit_axes.py`（106 fam EDIT_AXES 中心化配置, 316 axes, safe-direction 预挑）+ `pair_builder.py`（orig/GT code + STEP 导出 + JSONL + 增量 flush）
- `scripts/data_generation/cad_synth/pipeline/builder.py` `render_program_to_code(..., include_params_hint=False)` 新增 flag：顶部注入 `# --- parameters ---` 注释块。默认关闭，原管线 byte-identical
- Delta 策略：2-5% + 安全方向（inner→-, outer→+）；三层过滤：`validate_params` → axis constraints → 体积 ratio/bbox min sanity
- 1 root × 2 diff (easy+hard) × 3 axes × 1 delta × 2 levels = 12 records/family
- 跑全 106 fam（排除 worm_screw，OCCT 崩溃 → UA-16）→ 1228 pairs (614 L1 + 614 L2), 97.5% yield
- 产物：`data/data_generation/bench_edit/{pairs.jsonl, codes/, steps/, pair_stats.json}`
- 最低产量：bearing_retainer_cap 4（两 axis 走 disc 变体不出现，自动 skip）；其他 ≥6
- Pair builder 增量 flush（每家族一刷 pair+stats）防 OCCT C 层崩溃丢进度；`--exclude` CLI flag
- Runner + scorer 跑通（smoke 10 samples, gpt-4o）：
  - `bench/edit_gen/run_edit.py`：text-only OpenAI 调用，subprocess exec code → STEP
  - `bench/edit_gen/score_edit.py`：复用 `bench.metrics.compute_iou` → `norm_improve = (IoU(gen,gt) - IoU(orig,gt)) / (1 - IoU(orig,gt))`
  - 10/10 api+exec pass, gen_iou 0.9929, 6/10 degenerate（orig/GT IoU>0.999，ball_knob 小 delta 64³ voxel 测不出）
  - 产物：`runs/<model>/{gen_code, gen_step, results.jsonl, scored.jsonl, score_summary.json}`
- 遗留：degenerate rate 需要决策（pre-filter orig/GT IoU<0.99，还是升 voxel 到 128，还是承认作 easy signal）

## 2026-04-20 (session 16) — Bench E2E：view alignment (UA-18) + QA bench + HF 零本地依赖

- **UA-18 view alignment** DONE：
  - `bench/models/__init__.py` SYSTEM_PROMPT 从 front/right/top/iso → cadrille 对角视角 `[1,1,1]/[-1,-1,-1]/[-1,1,-1]/[1,-1,1]`
  - `bench/test/run_test.py` `_render_step` 换成真正存在的 `render_step_normalized`（之前 import `render_views` 从不存在，`--save-render` 静默失败半年）
  - GPT-4o 输入和 gen_render.png 现在用同一 cadrille renderer, 268×268 完全对齐
- **QA bench** 新增：
  - `bench/smoke_upload.py` schema +`qa_pairs`+`iso_tags` 两列（json str）
  - `bench/models/__init__.py` 新增 `QA_SYSTEM_PROMPT` + `call_vlm_qa(model, img, questions)` + `_parse_qa_answers`（严格 JSON array of numbers）
  - 新文件 `bench/eval_qa.py`：image + qa_pairs → VLM → numeric answers → `qa_score`（对称 ratio accuracy）
- **HF smoke re-upload**: `Hula0401/cad_synth_bench_smoke` 12 rows 加上 qa/iso 列 (235KB parquet)
- **E2E verify (gpt-4o, 12 samples)**：
  - Code bench: exec 58.3%, IoU 0.187, F1 0.139, detail 0.127
  - QA bench: parse 12/12, qa_score 0.562 (bevel_gear 0.857 最好，clevis_pin 0.389 最差)
- **README `bench/README.md`** 重写：vtk 只在 `--save-render` / upload 需要，GPT 默认 eval 不需要；一键启动、schema、指标定义全写清
- 发现 `synth_clevis_pin_001840/002950` gt_code 自己都跑不动（bad 样本进了 accepted 集） — 另开 task 清理

## 2026-04-19 (session 15) — +16 新 family (communication.md 12 + 3D-print 4)

- communication.md 工业标准件 12 个 (全按 DIN/ISO/MS 标准表):
  `u_bolt` DIN 3570 · `rivet` DIN 660 · `cotter_pin` ISO 1234 · `pull_handle` DIN 81396 · `pillow_block` ISO 113 UCP · `turnbuckle` DIN 1480 · `keyhole_plate` N/A (Häfele) · `pan_head_screw` ISO 1580 · `grommet` MS 35489 (XZ revolve H-profile) · `tee_nut` DIN 1624 (tapered prongs via `extrude(taper=)`) · `j_hook` DIN 3570 mod · `wall_anchor` ETAG 001 (longitudinal split slots + tapered tip revolve)
- 3D-print popular 4 个: `gridfinity_bin` (42mm cells + label lip + optional divider) · `hex_key_organizer` (ISO 2936 hex pockets) · `battery_holder` (IEC 60086 cells: AAA/AA/18650/21700) · `phone_stand` (angled wedge + cable slot + relief pocket)
- 关键 trick 发现: `Op("torus", ...)` 顶层 primitive 会**静默替换整个 workplane**（不是 union），所以 cotter_pin 改用 `union` 内嵌 `moveTo+circle+revolve(180°, axis=-Y)` 构造半环 (与 U-bolt bend 同 pattern)
- 全 16 fam × 3 diff preflight (build + render→exec roundtrip) 全通过；tmp/_preflight_new.py + tmp/_render_grid_new.py
- registry.py 注册 16 个；合成大图 `tmp/new_families_grid/new_families_16.png`

## 2026-04-19 (session 14) — UA-15 3 家族重做 (star_knob → lobed_knob, wing_nut, grease_nipple)

- **star_knob → lobed_knob**: DIN 6336 claim 撤销（旧实现只是 N-lobe 花瓣，轮廓/比例差 DIN 太远）
  - 文件 rename + 类 `LobedKnobFamily` + `standard="N/A"`；registry 同步
  - 几何保留（central disc + N lobe union + bush + through-hole），纯作非标训练 structure
- **wing_nut 重做** (DIN 315 rounded wings) — 按 user-verified `manual_wingnut.py` 完全照抄
  - 旧版用 box 翼板 → 新版 polyline+threePointArc 椭圆化翼轮廓，extrude both=True（±Y）
  - Arc 解析几何：`x=e/4+d2/4`, `R=(dX²+dZ²)/(2dZ)`，midpoint 按 atan2 角度插值
  - 9 档 DIN 315 (M3–M20)；M8 bbox 39.89×16×19.96 完美匹配 manual
  - 辅助 `_ear_polyline_ops(sign, ...)` 用 `sign=±1` 生成 +X / -X 翼 sub-ops（builder 不支持 `mirror("YZ")`，用坐标取反平替）
- **grease_nipple 重做** (DIN 71412 Type A) — 按 `manual_grease_nipple_adj.py`
  - 旧版 4-solid unioned (shank+hex+neck+sphere)  → 新版单一 revolve body (9-pt polyline on XZ → revolve 360° 绕 Z) + XY hex flange + axial bore
  - `base_plane="XZ"` 主 wp；hex 与 bore 用 `union`/`cut` sub-op `plane="XY"`
  - 头部 fixed geometry (h=16, l=5.5, d2=6.5, b=3.0, z=0.7)；6 规格 (d1, s 组合)
  - Top fillet / bottom chamfer 跳过：`edges(">Z")` 在 `base_plane="XZ"` 会被 `_remap_sel` 错误映射到 ">Y"（基底 plane normal = -Y）；cosmetic only
- **builder.py 增强**: `union` / `cut` sub-op 新增 `plane` 参数（默认为 `_current_base_plane`）→ 子 workplane 平面独立可选，execution + render_to_code 两路都支持
- 全 27/27 (3 fam × 3 diff × 3 seed) bbox & render→exec roundtrip 完全 match
- 88 data_gen tests pass；ruff + black clean

## 2026-04-19 (session 13) — `twisted_drill` follow manual 重写

- 按 `tmp/manual_family_previews/manual_twisted_drill.py` 重写 `families/twisted_drill.py`
- `_arc_midpoint` + `_build_cutter_wire_ops` 数学全按 manual verbatim 移植（Ca/Cb 双弧 + rim arc 闭环）
- 微观几何 fixed: `r_phi=0.18·R0`, `Ra=0.6·R0`, `phi_deg=30°`
- sample_params: R0 ∈ {1.0,1.5,...,10.0}, L/R0 ∈ [8,15], P/R0 ∈ [11,13.5] (γ≈28°), θ ∈ {118,130,140}
- validate_params: R0 ∈ [0.5,12], P ∈ [10R0,14R0], L ∈ [7R0,16R0], L > tip_height+2
- tip 削尖：manual 的 `body.intersect(envelope)` 在本 OCCT build 对大多数参数崩（仅 R0=4 L=40 P=47 θ=118 能过）
  → 改几何等价的 `body.cut(ring ∪ inner_notch)`：ring = cyl(2R0)∖cyl(R0)，inner_notch = cyl(R0)∖loft_cone(R0→apex)
  → 没有 intersect、只用 cut/union/loft/extrude，稳定性显著好过 manual
- 150+ 样本 fuzz: 97%+ OK，少量 zero_vol（OCCT 特定 P/L 组合数值不稳）由 runner `MAX_PARAM_RETRIES=10` 兜底
- render→exec roundtrip: R0=3 L=30 vol=365.6 完全匹配
- **Sliver fix**: cutter arcs 理论精确落在 R0 rim（tangent）→ OCCT 精度误差生成 sliver face；
  base disk outer_radius 从 R0 改为 0.99·R0 → cutter 干净穿透 rim。
  副作用：body 外径 R0 → 0.99·R0（体积 -2%，可忽略）
  Fix 后 50/50 fuzz 全 ok，zero_vol 归零
- 4 视觉 sample 渲染 OK；88 data_gen tests pass；ruff + black clean

## 2026-04-19 (session 12) — 移除 `twisted_joint` (UA-17 撤销)

- 2-section loft 产物视觉不是真正扭转（直纹 wedge），用户判定 不保留
- 清理：删 `families/twisted_joint.py`；registry 去 import+注册；TASK_QUEUE UA-17 标 REMOVED；memory 同步
- family 总数 91 → 90
- 备注：保留 `tmp/manual_family_previews/manual_twisted_joint.py` 作为未来平滑扭转 Op 的参考实现

## 2026-04-19 (session 11) — wing_nut + star_knob + grease_nipple (UA-15, 88-90)

- 新增 3 family: `wing_nut` (DIN 315), `star_knob` (DIN 6336), `grease_nipple` (DIN 71412 H1)
- 流程：communication.md 5 候选 → 过滤 2 冗余 (grooved_pin 与 dowel/clevis/taper_pin 重合; lifting_eye_nut 与 eyebolt 重合) → 手动原型 3 份 → Op 化 → pre-flight → render 验证 → 注册
- **wing_nut**: 中心 hex boss + 2 翼板 (box, ±X)，翼端 |Y fillet，M3–M16 (8 档)
- **star_knob**: 中心 disc + N lobe(circle 0.55·R_outer) union 成花瓣轮廓，下方 bush 突出，贯穿孔。N∈{3,5,6}, d_thread M5–M16
  - 顶/底 fillet 移除：union 后 top 面只剩 5 凹谷 edges，OCCT 任意半径都 fail (chamfer 也 fail)
  - 关键发现：`_apply_op` 的 fillet/chamfer 有 try/except 静默吞错 → Workplane 路径 "通过" 但 render→exec 路径裸抛 → 必须 roundtrip 验证才能发现
- **grease_nipple**: thread shank + hex collar + neck + sphere ball head + axial bore，ball d=6.5 固定 (DIN 71412 通用 grease-gun 接口)
  - validate 修正：`s*2/sqrt(3) > d` 而非 `s > d`（pipe thread d>AF 但仍入 hex across-corners）
  - R1/4 行修正 s=11→14, d_neck=4.5→5.0（11mm AF 夹不住 13mm 螺纹）
- 全 27/27 (3 fam × 3 diff × 3 seed) render→exec bbox 完全 match；9/9 composite PNG 视觉 OK
- 总 family 数 87 → 90；88 data_gen tests pass；ruff clean；black clean

## 2026-04-19 (session 9) — `twisted_drill` family + 4 new Ops (UA-14)

- 新增 87th family `twisted_drill` (DIN 338 麻花钻 type N)
- 几何: 两块 DIN 338 cutter 2D 轮廓（大 relief arc Ra + 小 back arc Rb + rim arc R0）→ sketch_subtract 从 outer circle 得到双槽刃面 → twistExtrude → cut "tip chimney" (big cyl ∖ cone-loft envelope) 刻点
- 全 hard 难度（twist + arc 微几何本质难度高，不分 easy/medium）; `standard="DIN 338"`
- `builder.py` 新增 4 Op + renderer：
  - `sketch_subtract` — 从 outer circle 减去多个 rotate_deg 配置的 wire profile 构造 `cq.Sketch`
  - `placeSketch` — 把 sketch 装到 Workplane
  - `twistExtrude` — `wp.twistExtrude(distance, angle)` 
  - `intersect` — （备用）`wp.intersect(sub_ops)`
  - Sketch 对象通过模块级 `_pending_sketch` / `_pending_sketch_code` 串连（同 `_current_base_plane` 模式）
- 关键坑：`body.intersect(cone_envelope)` OCCT intermittent "Bnd_Box is void" 崩溃 → 改 `body.cut(big_cyl ∖ envelope)` tip-chimney，稳定性 15/15 → 63/63 grid 全过
- 采样约束：`total_twist = 360·(L+5)/P < 340°`（> 365° twistExtrude self-overlap）
- 5 seed render→exec bbox 全 PASS；88 data_gen tests pass；ruff + black clean
- E741 `I` → `Ipt` 重命名

## 2026-04-19 (session 8) — bolt/knob/pulley/clevis_pin hard 修复

P0 — pulley keyway: cutThruAll 切穿全直径 → 改 cut(box) 在孔壁 (offset z=br+kh/2, height=kh)，槽只在 bore 表面
P1 — knob: 删 polarArray hole 假底洞、删 standard "DIN 319" (球钮)、加 12 个轴向 cylinder 切槽 (real grip flutes, 在 rt*1.05 处) + 顶 fillet + 底 chamfer
P2 — bolt threads: 阶梯轴 → 真 ISO V 螺纹。布局翻转使刀尖落在 z=0 (cq.Wire.makeHelix 世界坐标固定)，60° V 截面 swept 沿 helix。`isFrenet=False` 关键 (True 把刀截面旋成无效姿态分裂成 8 solid)
P3 — pulley spokes: 6 个矩形 cut box，但 transformed(offset, rotate) 实际 offset 先 / rotate 在新原点 → 6 cutter 全部聚在 (26,0)。改用 cos/sin 算 (fx,0,fz) world 位置，rotate 只用来转 box 朝向。axial view 验证 6 spoke 均匀分布
P3 — pulley width: groove_w + 2*flange → max(..., pd_mm * 0.18) ISO 22 最小比例
preflight 4 family × 3 diff 全通过；88 data_generation tests pass；ruff clean；black clean
clevis_pin lint: l → ln 重命名 (E741)

## 2026-04-18 (session 7c) — coil_spring 纯扫掠重写

- 删除所有 grind / box cut / union 逻辑 — 任何 spring = 单次 sweep 圆截面
- 3 个 difficulty 仅 wire_d / n_coils / spring_index 参数范围不同，几何操作完全相同
- 删除死参数 `tight_coils` / `tight_pitch` / `tight_height`；删除 `grind_depth`
- `height` 精度 `round(..., 6)` 保留整圈精度（与 torsion_spring 对齐）
- 3×3 preflight 9/9 通过；9 样本均为纯螺旋线圈
- 29 tests pass; ruff clean; black clean

## 2026-04-18 (session 7b) — torsion_spring 单次 sweep 重写

- 旧实现: coil 单独 sweep + 2 腿用 `union` 垂直挤出（`rotate=[90,0,0]` → -Y）
  - Bug: 腿的方向 ≠ 螺旋切线 (t=0 切线 = (0, R, p/(2π))/mag，有 Z 分量)
  - 腿和螺旋端面成角度，不是切向相接 — 用户反馈 sample 5657 错
- 新实现: 完全 follow `tmp/manual_family_previews/manual_torsion_spring.py`
  - 单次 sweep：one circle profile 沿 combined wire (leg1 + helix + leg2) 扫一次
  - 新增 `path_type="helix_with_legs"` 到 `builder.py`（apply + code-gen）
  - 腿方向 = helix 实际端点处参数化切线（容忍非整圈）
  - 删除 hook / grind（manual 没有）
- Bug fix 2: `height = round(pitch × n_coils, 1)` 破坏 exact integer turns
  → helix 端点不落在 (R,0,H) → wire 装配失败 (`BRep_API: command not done`)
  改为 round 到 6 位保留精度
- 3×3 preflight 9/9 通过；视觉：正确的切向腿 + 标准螺旋线圈
- 生成代码包含 `_helix_with_legs_path` helper，可独立执行（验证通过）

## 2026-04-18 (session 7) — batch_2k_apr18b 全 85 family 生成

- 配置：2000 samples, seed 4185, 8 workers, 全 85 family × 3 difficulty 均匀
- 结果：1987/2000 accepted (99.4%)；13 rejected = build_failed timeout>180s
- 全 5 new families (torsion_spring/eyebolt/spline_hub/venturi_tube/double_simplex_sprocket) 参与采样
- 输出：`data/data_generation/generated_data/fusion360/synth_*_s4185/` (5.9 GB)
- 全 85 family preflight 255/255 OK；88 cad_synth tests pass；ruff clean

## 2026-04-18 (session 6b) — `twisted_bracket` family (UA-13)

- 新增 `twisted_bracket` (86 total) — 无 ISO, 物理合理
- 几何: 两块垂直薄板沿 X 轴并排 + 短 YZ-loft 90° 扭转连接
  - Plate 1 (XY, 厚度 Z) → twist (loft between 2 YZ rect, 第二个绕 X 旋转 90°) → Plate 2 (XZ, 厚度 Y)
  - 关键: twist 端面用 chained `transformed` — `rotate[0,90,0]` 后再 `rotate[0,0,90]` 实现扭转
  - 每板 1 或 2 螺栓孔（方向：Plate1 沿 Z 切，Plate2 沿 Y 切）
- 第一次实现是沿 Z 堆叠的扭转棱柱 — 视觉上像扭转 wedge，不像两块垂直板。重写为侧并排布局
- 3×3 preflight 8/9 通过；18-sample batch 100% 通过；视觉正确
- registry 注册；29 data_gen 测试通过；black + ruff clean

## 2026-04-18 (session 6) — 4 new families + `torus` Op (UA-11, UA-12)

- 新增 4 family (85 total，从 81)：
  - **eyebolt** (DIN 580, M8–M20) — collar + shank + neck-loft + torus eye ring
  - **spline_hub** (DIN 5480) — hub cyl + 内齿切削 (threePointArc × 4z 闭合线) + DIN 509-F undercut + chamfer
  - **venturi_tube** (ISO 5167-4) — 闭合壁厚截面 polyline → revolve 360° around Y
  - **torsion_spring** (DIN 2088) — helix sweep coil + 2 切线 leg + 可选 hook/grind（之前已写，本次注册）
- 新增 `torus` Op 到 builder（`cq.Solid.makeTorus(major, minor, pnt, dir)`）—
  eyebolt 需要，因 `revolve` 圆心在旋转轴上时 OCCT 报 `BRep_API: command not done`
- 4 family × 3 difficulty × 3 trial pre-flight = 36/36 build 通过；视觉审核 4/4 通过
- `registry.py` 注册 3 新 import + 3 新 entry
- 88 data_generation tests 通过；black + ruff clean

## 2026-04-18 (session 5) — P2 WARN audit + fixes (10 families)

- 10 P2 WARN families fixed after fresh-render verification:
  - **clevis_pin** — REAL BUG: hard circlip groove was `rect cutThruAll on XZ` (cut a rectangular slice through pin); rewritten as annular ring groove (cut outer cyl + union back inner core)
  - mounting_plate — corner holes at all difficulties (was medium+); fillet → medium/hard
  - vented_panel — easy/medium hole_d ≥ min(plate)/15-18; max bumped 12→14, 10→12
  - dovetail_slide — variant bias 70% female at easy/hard (was 50/50)
  - cam — eccentricity ≥ 0.22×r_base (was 0.10); lobe ≥ 0.18×r_base (was 0.10)
  - flat_link — bore_radius at all difficulties (was medium+); range 0.30–0.55×boss
  - rect_frame — side_slot_depth ≤ 0.40×rail capped 7mm (was 0.55, 10mm) — avoids wireframe
  - sheet_metal_tray — easy sheet_thickness ≥ 2.5mm (was 1.0); rim now visible at iso scale
  - mounting_angle — depth cap 4×leg (was 6×) — avoids spindly/sliver look at medium
  - pcb_standoff_plate — post_h ≥ 8mm + post_od ≥ 6mm (was 4/4); inset ≥ 8mm
  - connector_faceplate — primary cutout pushed to left half, secondary to right (avoid diamond)
- Methodology: render 4-view 512px composite → visual diff → tighten params or fix geometry
- Tally update: 75 PASS · 6 WARN · 0 FLAG (was 65/16/0)
- 29 cad_synth tests pass; black + ruff clean (pre-existing E741 in clevis_pin unchanged)

## 2026-04-18 (session 5) — 81-family deep audit (P1 FLAGs)

- **Phase 1**: batch_audit_apr18 = 1500 samples, all 81 families × 3 difficulties (seed 5184)
- **Phase 2 quick scan** (per-family 6-sample montages):
  - 56 PASS · 17 WARN · 11 FLAG (initial)
- **Phase 3 deep audit** of P1 FLAGs:
  - **pulley** — REAL BUG fixed: V-groove half-width was `gd/tan(ga)` → corrected to `gd*tan(ga/2)`; spoke pockets rotated around Z axis (wrong) → Y axis (matches revolve axis); 9 preflight builds OK
  - **spacer_ring** — REAL BUG fixed: hard split-ring generated 180° half-ring → rewritten as full ring + narrow radial slit (snap-on style); docstring updated to mark non-DIN variant
  - **stepped_shaft** — REAL BUG fixed: easy proportions allowed h2<h1 → enforces h2 ≥ 1.5×h1 and r2 ≤ r1×0.7 for clear hub+shaft profile; validate also tightened (r2 ≥ r1×0.75 → reject)
  - **table, chair, enclosure** — false flags (geometry correct, render artifacts at iso-view scale)
  - **hollow_tube, capsule, l_bracket** — false flags (fresh re-renders confirm correct topology)
  - **pipe_flange** — false flag (square plate flange is intentional; round_flange is separate family)
  - **bearing_retainer_cap** — false flag (ear variant = boss + 2 ear tabs is intentional)
- Final tally: 65 PASS · 16 WARN · 0 FLAG
- 29 cad_synth tests pass; black + ruff clean

## 2026-04-18 (session 4)

- Visual audit (6 parallel subagents): all 33 standardized families PASS — 76/76 renders correct
  - Two false-alarm issues: threaded_adapter (old renders pre-rewrite), parallel_key easy (subagent misread table range)
- Sprocket pass-1 rewrite — fix incorrect "bumps" topology:
  - OLD: root disc + union small bumps → smooth washer (no teeth visible)
  - INTERIM: tip disc (Ra) + cut z seating cylinders → correct ISO 606 tooth spaces but straight flanks
- Sprocket pass-2 rewrite — continuous polyline + chamfer per `manual_double_sprocket.py`:
  - Single CCW polyline outline (root arc + flank line + tip midpoint × z) → one-shot extrude
  - chamfer >Z + chamfer <Z BEFORE bore (chamfer only outer perimeter)
  - keyway via cutThruAll (was cutBlind)
  - ISO 606: do=dp+0.6*dr, ri=0.505*dr, β/2=(140°-90°/z)/2
  - Helper `iso606_sprocket_profile()` lives in base.py — reusable
- Added double_simplex_sprocket family (DIN 8187 / ISO 606):
  - Full-length central hub + 2 unioned toothed discs (each polyline+chamfer in union sub-ops)
  - spacer_diameter sized between bore*1.6 and df*0.75
  - spacer_w = b1 * [1.5..2.5], axial layout: [disc1:b1][hub gap:spacer_w][disc2:b1]
  - Visual matches https://australia-drive.com/.../08b-1-double-simplex-sprocket
  - Registered in registry.py
- 18 preflight builds pass (2 families × 3 difficulties × 3 trials), 88 tests pass
- Added `scripts/data_generation/cad_synth/AUDIT_METHODOLOGY.md` — 9-step
  visual-audit workflow + common-pitfalls table for re-auditing other families

## 2026-04-18 (session 3)

- UA-7 完成：8个 Tier C family 标准化修复 (240/240 qa_generator tests pass)
  - threaded_adapter: 加 ASME B1.20.1 NPT 9-row 尺寸表，替换全部 14 个 rng.uniform
  - spur_gear: z→rng.integers, face_w→b/m∈{6,8,10,12}×m, keyway→DIN 6885A
  - helical_gear: 同 spur_gear + helix_angle→choice([15,20,23,25,30])
  - bevel_gear: pitch_angle→choice([15..40]), face_w→b/m∈{4..8}×m
  - pulley: 以 ISO 4183 belt section 为锚重构 sample_params; ISO 22 PD 表驱动
  - sprocket: disc_thickness→dr×choice([0.8..1.3])
  - t_slot_rail: slot_depth/back_w/wall_t 改为 DIN 650 profile 固定值
  - hex_standoff: flange_od/bore_step 改为离散倍数
- UA-8 完成：33个有标准 family 全部在 docstring 加 Reference 来源（标准号+文档标题）
- 88 tests pass

## 2026-04-18 (session 2)

- UA-6 完成：所有 Tier 2 families 补全 ISO/DIN 表格驱动
  - bevel_gear: ISO 54 module + `rng.integers` for tooth count + DIN 6885A keyway
  - sprocket: DIN 6885A keyway (replaced proportional formula)
  - pulley: ISO 22 groove angles + ISO 4183 belt section table (done in session 1)
  - rect_frame: corrected standard N/A (EN 10219 doesn't apply); preferred-size table added
- Added `din6885a_keyway()` helper to `base.py` (shared DIN 6885A lookup)
- Bug Fix: spur_gear/helical_gear web recess + rim_boss verified (100% build pass)
- Preflight: propeller/manifold_block/lathe_turned_part all 9/9 build OK

## 2026-04-18 (session 3)

- Standardized all 80 families:
  - Easy wins (already table-driven, just needed `standard =`): i_beam (EN 10034), u_channel (EN 10279), clevis_pin (ISO 2340)
  - Added tables: coil_spring (DIN 2095 wire diameters), t_pipe_fitting (ASME B16.9 NPS), clevis (DIN 71751)
  - Added `din6885a_keyway()` helper to base.py (shared by bevel_gear, sprocket, and others)
  - All 44 custom/application-specific families set to standard = "N/A"
- Launched batch_2k_apr18: 2000 samples, all 80 families, seed 2418, 8 workers
