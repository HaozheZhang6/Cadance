# TASK QUEUE

---

## ⚠️ USER-ASSIGNED — 进行中

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

## 已完成

| Task | 完成时间 | 说明 |
|------|---------|------|
| UA-2 t_pipe_fitting 装配顺序 | 2026-04-17 | branch cut → main bore cut 顺序正确 |
| UA-3 handwheel DIN 950 修复 | 2026-04-18 | centered cylinder offsets, validate_params, handle |
| t_pipe_fitting visual 验证 | 2026-04-18 | 与 manual 对比 OK |
| UA-5 standard 列 + 28 families | 2026-04-18 | BaseFamily.standard + exporter standard column; 28 families set |

---

## Bug Fix Queue

| Bug | 优先级 | 状态 |
|-----|--------|------|
| spur_gear/helical_gear annular web recess 验证 | ⭐ HIGH | 待渲染验证 |
| spur_gear rim_boss 配套 hub_boss | ⭐ HIGH | 待验证 |
| sprocket DIN 8187 参数不符 | 🟡 MED | 待修 |
| bearing_retainer_cap ear bolt hole 圆角 | 🟢 LOW | 待下批次 |

---

## Pending 渲染验证

- `propeller` — 参考 `tmp/manual_family_previews/manual_propeller.py`
- `manifold_block` — 参考 `tmp/manual_family_previews/manual_manifold_block.py`
- `lathe_turned_part` — 参考 `tmp/manual_family_previews/manual_lathe_turned_part.py`
