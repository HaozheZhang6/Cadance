# TASK QUEUE

---

## ⚠️ USER-ASSIGNED — 进行中

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
