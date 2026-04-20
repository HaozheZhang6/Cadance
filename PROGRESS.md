
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
