# MechEval: CAD Benchmark — NeurIPS Plan

*Last updated: 2026-04-16*

---

## 核心卖点 vs CAD-Evolve

| | CAD-Evolve | MechEval（我们） |
|--|--|--|
| 任务 | 图→代码（形状重建） | 图→代码 + **参数逆向** + **ISO合规** |
| 数据 | 真实CAD模型 | 合成，参数完全可控 |
| Metric | IoU / CD | IoU / CD / Feature-F1 / **QA-Score** / **ISO Compliance** |
| 工业价值 | 形状还原 | 还原可制造的**工程参数** |
| 可扩展性 | 依赖真实数据采集 | 参数化生成，可无限扩展 |

**核心Narrative**（Intro一句话）：
> 现有3D生成模型输出的是"死几何"——视觉上逼真但缺乏工程语义。MechEval是第一个要求模型从图像中恢复**ISO工业标准参数**的benchmark，将AI-CAD从形状拟合推向真正可制造的设计理解。

---

## 任务定义（3个）

```
Task A — 图→代码（形状重建）
  输入：4-view composite render
  输出：CadQuery代码
  评估：exec_ok + IoU + CD + Feature-F1 + detail_score

Task B — 图→参数（视觉参数逆向）
  输入：4-view composite render + question
  输出：数值答案（e.g. 齿数=20，模数=2.0）
  评估：QA-Score (0-1)

Task C — 代码→参数（代码语义提炼）
  输入：hardcoded CadQuery脚本 + question
  输出：数值答案
  评估：QA-Score (0-1)
  意义：LLM能否从`circle(20)`推断出m*z/2=20？
```

Task B vs Task C 的对比揭示：**模型理解形状 vs 理解代码的本质差异**。

---

## 数据架构（双轨制）

```
sample_params()   →  params dict         ← "有语义的灵魂" (GT)
     ↓                    ↓
make_program()    →  hardcoded CadQuery  ← "无语义的表象" (Task输入)
     ↓                    ↓
render()          →  4-view PNG          ← Task A/B输入
                       qa_pairs          ← Task B/C的问题+GT答案
                       iso_tags          ← ISO合规元数据
```

这个双轨制我们**已有**，只是没显式建模成eval任务。
`params`在每个样本的`meta.json`里，现在同步到HF数据集。

---

## HF数据集字段（Hula0401/cad_synth_bench）

| 字段 | 类型 | 说明 |
|------|------|------|
| stem | str | 唯一ID |
| family | str | 零件族 |
| difficulty | str | easy/medium/hard |
| base_plane | str | XY/XZ/YZ |
| split | str | test_iid/test_ood_family/test_ood_plane |
| feature_tags | JSON | has_hole/fillet/chamfer |
| feature_count | int | feature_tags中True的数量 |
| ops_used | JSON | 用到的CadQuery操作 |
| gt_code | str | hardcoded CadQuery（Task C的输入） |
| composite_png | PIL Image | 4-view合图（Task A/B的输入） |
| **qa_pairs** | JSON | 1-3个QA对，含GT答案+类型+tolerance |
| **iso_tags** | JSON | 适用ISO标准+关键派生值 |

---

## QA设计

### 评分函数
```python
# 整数（齿数、孔数）
score_integer: exact=1.0, ±1=0.5, else=0.0

# 连续/比值（模数、长径比）
score_continuous: max(0, 1 - |pred-gt| / (tol * gt))
# tol: 5%（精密参数如模数）/ 8%（比值）/ 10%（整体尺寸）
```

### 各family的QA示例

| Family | Q1 | Q2 | Q3 |
|--------|----|----|-----|
| spur_gear | 齿数 (integer) | 模数mm (5%tol) | 分度圆径mm |
| helical_gear | 齿数 | 模数 | 螺旋角° |
| bevel_gear | 齿数 | 模数 | 节锥角° |
| bolt | 长径比 (8%tol) | 杆径mm | 螺距mm |
| pipe_flange | 螺栓孔数 (integer) | 法兰径/管径比 | — |
| t_pipe_fitting | 壁厚比 | 外径mm | 螺栓孔数 |
| coil_spring | 有效圈数 (integer) | 弹簧指数 | — |
| heat_sink | 翅片数 (integer) | 翅片高/底座比 | — |
| stepped_shaft | 长径比 | 台阶数 (integer) | — |
| impeller/propeller | 叶片数 (integer) | 轮毂/叶尖径比 | — |

**20个family已覆盖**，其余family返回空QA（不影响整体eval，仅Task B/C样本数会少）。

---

## ISO合规设计（当前：gear → 扩展中）

### 已实现：spur_gear (ISO 53)

```python
# ISO 53 齿轮合规分数
def iso53_compliance(m_pred, z_pred, da_pred, df_pred, d_pred):
    da_gt = m * (z + 2)    # 齿顶圆
    df_gt = m * (z - 2.5)  # 齿根圆
    d_gt  = m * z           # 分度圆
    return 1 - mean_rel_error([da, df, d])
```

`iso_tags`示例（spur_gear）：
```json
{
  "iso_53": true,
  "module": 2.0,
  "n_teeth": 20,
  "pressure_angle_deg": 20.0,
  "pitch_diameter_mm": 40.0,
  "tip_diameter_mm": 44.0,
  "root_diameter_mm": 35.0,
  "iso_1328_grade": 7
}
```

### 扩展计划

| Family | ISO标准 | 核心参数 | 状态 |
|--------|---------|---------|------|
| spur_gear | ISO 53, ISO 1328 | m, z, da, df | ✅ 已实现 |
| helical_gear | ISO 53 | m, z, β, da, df | ✅ 已实现 |
| bevel_gear | ISO 23509 | m, z, cone_angle | ✅ 已实现 |
| worm_screw | ISO 1122 | m, n_starts | ✅ 已实现 |
| bolt | ISO 261 | d, pitch, length | ✅ QA已实现 |
| hex_nut | ISO 4032 | d, s | ✅ QA已实现 |
| pipe_flange | ISO 7005 | OD, PCD, n_bolts | ✅ QA已实现 |
| t_pipe_fitting | ISO 1127 | OD, wall | ✅ QA已实现 |
| stepped_shaft | ISO 286 | d, tolerances | ✅ QA已实现 |
| coil_spring | ISO 2162 | n_coils, index | ✅ QA已实现 |
| **bearing_retainer_cap** | ISO 281 | bore_d, PCD | 🔲 待做 |
| **hex_standoff** | ISO 4766 | d, length | ✅ QA已实现 |

**下一步**：对gear family做端到端review（生成→QA→eval），确认后再推广到其他family。

---

## Metrics体系（完整）

```
Task A:
  exec_ok      : 代码能执行 (0/1)
  iou          : 体素IoU @64³ (0-1)
  chamfer      : CD (越低越好)
  feature_f1   : hole/fillet/chamfer F1 (0-1)
  detail_score : 0.4×iou + 0.6×feature_f1  ← 主排名指标

Task B/C:
  qa_score     : QA对的平均得分 (0-1)
    └ integer  : exact=1.0, ±1=0.5
    └ continuous: max(0, 1 - |Δ|/(tol×gt))

ISO Compliance（gear专项）:
  iso53_score  : 齿顶/齿根/分度圆与ISO 53公式的符合程度 (0-1)
  重要: IoU高 但 iso53_score低 = 视觉像但工业废品
```

**主报告格式**：
```
Model         | Exec% | IoU  | Feat-F1 | Detail↑ | QA-Score | ISO-Comp
GPT-4o        |  .XX  | .XX  |   .XX   |   .XX   |   .XX    |   .XX
GPT-5.2       |  .XX  | .XX  |   .XX   |   .XX   |   .XX    |   .XX
Qwen2-VL      |  .XX  | .XX  |   .XX   |   .XX   |   .XX    |   .XX
Cadrille-SFT  |  .XX  | .XX  |   .XX   |   .XX   |   .XX    |   .XX
```

---

## 数据集规模（当前状态）

| Split | 样本数 | 状态 |
|-------|--------|------|
| test_iid | ~660 | ✅ HF已上传 |
| test_ood_family | ~330 | ✅ HF已上传 |
| test_ood_plane | ~340 | ✅ HF已上传 |
| **总计** | **~1330** | batch_2k_apr15（1971 accepted → 1330 入bench） |

HF dataset: `Hula0401/cad_synth_bench`
GitHub eval: `miachen0401/mech_eval`

---

## 已完成

- [x] 74 families合成管线（multi-plane, easy/medium/hard）
- [x] 渲染管线（4-view + composite，camera=-0.9）
- [x] 2000-sample batch生成 + HF上传（batch_2k_apr15）
- [x] bench/ 重构：dataloader / metrics / models / render / research
- [x] 端到端eval脚本（bench/eval.py + bench/test/run_test.py）
- [x] gpt-5.x max_completion_tokens兼容
- [x] SYSTEM_PROMPT加4-view相机角度说明
- [x] **qa_generator.py**：20个family的QA模板 + ISO tags
- [x] **bench/metrics**: qa_score() + iso53_compliance()
- [x] exporter.py集成qa_pairs + iso_tags
- [x] t_pipe_fitting bug修复（operation顺序 + 只保留T型）
- [x] snap_clip bug修复（flange孔间距 > 孔径）
- [x] mech_eval GitHub repo同步

---

## 待做（按优先级）

### P0 — gear ISO端到端review
- [ ] 从HF取一个spur_gear样本，验证qa_pairs内容
- [ ] 用gpt-5.2做Task B测试（图→回答齿数/模数）
- [ ] 评估qa_score，检查问题是否合理
- [ ] review通过后：离线给HF数据集所有样本补充qa_pairs/iso_tags

### P1 — HF数据集更新
- [ ] push_bench_hf.py加qa_pairs/iso_tags两列
- [ ] 重新上传（或用datasets库patch现有版本）

### P2 — eval.py集成Task B/C
- [ ] Task B prompt设计（few-shot数字提取）
- [ ] Task C prompt设计（代码→参数推断）
- [ ] 加到bench/eval.py主流程

### P3 — 扩展ISO覆盖
- [ ] bearing_retainer_cap → ISO 281
- [ ] 其他fastener family验证

### P4 — baseline跑完整eval
- [ ] gpt-5.2 全量Task A（1330 samples）
- [ ] gpt-5.2 Task B（有QA的样本子集）
- [ ] 生成完整报告表格

---

## 未解决的问题

1. Task B/C的prompt：few-shot几个例子合适？需要实测
2. HF数据集patch：datasets库支持incremental column add吗？还是要整体重传？
3. ISO compliance metric的权重：iso53_score单独报告，还是并入detail_score？
4. QA的语言：英文问题 vs 中英文混合？（影响不同LLM的表现）
