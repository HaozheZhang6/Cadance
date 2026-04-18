# TASK QUEUE

---
## ⚠️ USER-ASSIGNED — 待确认/待完成 (2026-04-17)

### UA-1 — ISO 标准参考库 (Codex 做数据收集) 🔴 HIGH
**目标：** 为每个有 ISO/DIN 标准的 family，建立一个 `references/<family>/` 子文件夹，包含：
1. 标准参数表格（从权威来源抓取/整理，必须注明 URL 来源）
2. 带标注的图片（param 名称对应 ISO 图纸标注，例如 OD/ID/PCD/tooth_profile）
3. 一个 `README.md` 说明该 family 对应的 ISO/DIN 标准号

**执行方式：** 用 Codex CLI (`codex`) 对每个 family 搜索并整理信息

**已知问题示例：**
- `sprocket` — URL: https://australia-drive.com/product/08b-1-double-simplex-sprocket-for-roller-chains-din-8187-iso-r-606/
  - 现有参数不符合 ISO/DIN 8187 / ISO R-606
  - 需要 pitch, number of teeth, roller diameter, plate thickness 等标准表格
- 每个 family 的 `sample_params` 必须以这些表格为依据更新

**输出结构：**
```
references/
  sprocket/     # DIN 8187 / ISO R-606
    table.md    # 标准参数表（必须有 URL 来源）
    diagram.md  # param 标注说明
    README.md
  hex_bolt/     # ISO 4014
  hex_nut/      # ISO 4032
  ... (所有有 ISO 的 family)
```

**状态: 未执行**

### ✅ UA-2 — t_pipe_fitting 装配顺序 (DONE 2026-04-17)
**用户要求的正确顺序（参考代码如下）：**
1. 先独立制作竖直支管并掏空（hollow branch tube）
2. 制作主体外壳（实心主管 + 法兰 + 加强座）
3. 法兰打孔
4. Union 预制好的空心支管进来
5. **最后** 掏空主管内孔（cut main bore）

**参考 CadQuery 逻辑：**
```python
# Step 1: 独立制作空心支管
branch_tube = cylinder(branch_len, branch_outer_r).cut(cylinder(bore_len, branch_inner_r))

# Step 2: 主体（实心）
result = cylinder(main_len, main_outer_r)
  .union(bottom_flange).union(top_flange).union(branch_boss)
  # Step 3: 法兰打孔
  .faces(">Y").polarArray(...).hole(...)
  .faces("<Y").polarArray(...).hole(...)
  # Step 4: Union 空心支管
  .union(branch_tube)
  # Step 5: 最后掏主孔
  .cut(cylinder(main_bore_len, main_inner_r))
```

**当前代码错误：** 先 union 所有 solid 再统一 cut，导致主管内孔穿透支管结构不正确
**文件：** `scripts/data_generation/cad_synth/families/t_pipe_fitting.py`
**状态: 未修复**

### ✅ UA-3 — handwheel DIN 950 碟形 (DONE 2026-04-17)
- 完全重写：hub 居中 z=0，rim 偏移 dish mm（DIN 950 表格精确值）
- 辐条：polyline 梯形截面 + extrude(both=True)，正确连接 hub/rim 两端
- Handle：绝对坐标定位，放在辐条间隙中间
- 参考 `tmp/manual_family_previews/manual_handwheel.py` 实现

### UA-4 — CLAUDE.md 任务追踪机制 🟡 MED
- 用户希望更新 CLAUDE.md，确保我不会遗忘指派的任务
- 想法待讨论后写入
- **未执行**

---

**核心目标：构建 CAD SFT 数据对**

每个数据对包含：
```
GT-normalized STEP          ← 归一化几何 bbox → [-0.5, 0.5]³
CQ code (IoU > 0.99)        ← 纯参数化代码，不能内嵌 STL/STEP/JSON 数据
ops JSON (最好有)            ← 描述性建模程序 (cut_hole/cut_pocket 格式，非原始 F360 JSON)
bad code + error_type        ← 可选，用于 correction pairs
```

**数据来源：** Fusion360 Gallery (8625 stems) + DeepCAD (待接入)

**SFT 组装条件：** 等 gt_norm_step_path、norm_cq_code_path、ops_program_path 都批量完成后再组装

---

## 当前状态 (2026-04-10)

### synth_parts pipeline
| 批次 | 时间 | 样本数 | 备注 |
|------|------|--------|------|
| smoke_all_families_apr11 (s5555) | 2026-04-10 | 1500 total, 157 deleted (5 bad fams) | 1343 good remain |
| apr12 | 待跑 | — | 修完5个family后跑 |

### 本次修复完成的 families (2026-04-10)
| family | 问题 | 修复方式 |
|--------|------|---------|
| enclosure | 全封闭看不出空心 | 改成浅盘 (h=12-40mm) open-top，从35°俯角能看进去 |
| hollow_tube | 管子太长，截面看不见 | X轴方向管，长度限制 0.6-2.0×宽度 |
| hinge | knuckle在叶片中心不可见 | 单叶设计，knuckle从右边缘挤出 |
| worm_screw | 螺纹没生成（位置错误） | workplane_offset→transformed(offset=[helix_r,0,z]) |
| bellows | 法兰太大像线轴 | flange_r改1.05-1.15x（原1.2-1.8x），conv_h加深 |

### cad_synth families 进度
| family | 状态 | 备注 |
|--------|------|------|
| spur_gear | ⚠️ 待渲染验证 | annular web recess; rim/hub互斥 |
| helical_gear | ⚠️ 待渲染验证 | annular web recess; 互斥 |
| bevel_gear | ✅ 完成 | cutBlind auto-negate fix |
| round_flange | ✅ 完成 | raised_face+neck bore fix |
| bellows | ✅ 修复 | flange缩小 1.05-1.15x; conv_h加深 |
| impeller | ✅ 完成 | back_plate+hub+swept blades+front_ring |
| pipe_elbow | ✅ 完成 | radiusArc elbow; neck+plate flanges |
| propeller | ⚠️ 待对比更新 | |
| t_pipe_fitting | ✅ 完成 | tee/cross only; 螺孔间距修复 |
| threaded_adapter | ✅ 完成 | bore at all difficulties |
| manifold_block | ⚠️ 待对比更新 | |
| cam | ✅ 完成 | hub boss; oil hole |
| lathe_turned_part | ⚠️ 待对比更新 | |
| bearing_retainer_cap | ✅ 完成 | disc+ear; tangent web; overlap fix |
| shaft_collar | ✅ 完成 | 简单圆环+孔; hard=双层hub |
| rib_plate | ✅ 完成 | 去掉cross ribs |
| sheet_metal_tray | ✅ 完成 | |
| z_bracket | ✅ 完成 | |
| tapered_boss | ✅ 完成 | |
| motor_end_cap | ✅ 完成 | |
| i_beam | ✅ 完成 | 简化 |
| enclosure | ✅ 修复 | 浅盘open-top |
| hollow_tube | ✅ 修复 | X轴方向，短管 |
| hinge | ✅ 修复 | 单叶+边缘knuckle |
| worm_screw | ✅ 修复 | transformed offset定位螺纹 |

---

## TODO Queue (按优先级)

### ✅ DONE — apr12 batch (314 accepted, 2026-04-10)
- bellows/hollow_tube/hinge/enclosure/worm_screw all fixed
- Run: `smoke_all_families_apr12`, seed 6666

### ✅ DONE — base_plane diversity (2026-04-10)
- XY/YZ/XZ randomly assigned per sample (33% each)
- smoke_plane_test: XY=61, YZ=29, XZ=30 (120 accepted)
- worm_screw + coil_spring forced XY (helix constraint)
- bearing_retainer_cap ~25% rejection rate on non-XY (OCCT bool — acceptable)

### TODO-1 — 验证 spur_gear / helical_gear 渲染 ⭐ HIGH
- 检查 GID 31517/31521/31530 等 (smoke_plane_test), 确认 annular web recess 正确
- 如有问题继续修

### TODO-3 — 对比更新 propeller / manifold_block / lathe_turned_part ⚠️ MED
- 参考 `tmp/manual_family_previews/` 里的手写文件
- propeller: `tmp/manual_family_previews/manual_propeller.py`
- manifold_block: `tmp/manual_family_previews/manual_manifold_block.py`
- lathe_turned_part: `tmp/manual_family_previews/manual_lathe_turned_part.py`

### TODO-4 — 大批量 synth 生成 ⚠️ MED
- 等全部 family 确认 OK 后，跑 10000+ 样本
- 需要配置好 GPU / 并发渲染

### TODO-5 — SFT 数据组装
- 条件: gt_norm_step_path + norm_cq_code_path + ops_program_path 都填充完
- 脚本: `scripts/data_generation/sft/`

---

## Bug Fix Queue

### BUG-3 — spur_gear/helical_gear web recess annular 验证 ⚠️
- 代码已改 annular切（`circle(wcr).circle(hub_keep_r).cutBlind`）
- 待 apr12 渲染验证

### BUG-4 — spur_gear rim_boss 没有配套 hub_boss ⚠️
- 代码已改 rim+hub同高
- 待 apr12 渲染验证

### BUG-9 — bearing_retainer_cap ear bolt hole 圆角 (低优先级)
- 低优先级；待下批次

---

## builder.py / pipeline
| 修复 | 状态 |
|------|------|
| cutBlind auto-negate (±depth both faces) | ✅ 完成 |
| GID search in UI | ✅ 完成 |
| SYNTAX_ERRORS.md | ✅ 完成 |

---

## 当前状态 (2026-04-02)

| 字段 | 填充率 |
|------|--------|
| verified rows (verified_parts.csv) | **1,635** |
| sft_ready=True | 1,567/1,635 |
| norm_cq_code_path | 1,567/1,635 |
| synth_parts.csv (smoke run) | 31,175 accepted (as of 2026-04-10) |
