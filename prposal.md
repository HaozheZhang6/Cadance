### ⚠️ UA-9 — 新增单体标准件 (Single-Body Standard Parts) 待开发队列

**目标：**
扩充 CadQuery 数据库，引入具有高价值特征（交叉切除、渐开线、螺旋扫掠、非线性比例）的单体标准件，所有参数必须由 ISO/DIN 离散表驱动。

> **已对 2026-04-18 现有 80 families 做过去重**：
> - `clevis_pin` (ISO 2340) 已实现 → 本列表删除
> - `compression_spring` (DIN 2095) 与现有 `coil_spring` 重叠 → 改为**升级**任务

#### 🟢 Phase 1: Low Hanging Fruit (极易实现，纯几何组合与表驱动)
这类零件逻辑简单，纯靠尺寸表约束，适合快速上线以扩充基数。

- [ ] **`woodruff_key` (半圆键)**
  - **标准:** DIN 6888
  - **核心逻辑:** 宽度 $b$ 和高度 $h$ 查表，反推半圆半径。
  - **区分 `parallel_key`:** 底面圆弧 vs 矩形平底。
- [ ] **`set_screw` (紧定螺钉/机米螺丝)**
  - **标准:** ISO 4026 (平端) / ISO 4027 (锥端) / ISO 4028 (圆柱端) / ISO 4029 (凹端)
  - **核心逻辑:** 内六角/一字槽 + 查表驱动的尾部几何演变。
  - **区分 `bolt`:** 无头，四种尾端 = 4× 负空间特征价值。

#### 🟡 Phase 2: Medium (中等难度，包含特定的3D布尔运算与薄壁)
这类零件需要处理交叉切槽、法兰轮廓以及薄壁特征，能为数据集提供极佳的负空间（Negative Space）特征。

- [ ] **`slotted_nut` (开槽螺母)**
  - **标准:** DIN 935
  - **核心逻辑:** 六角头 + 圆柱凸台 + 严格对应公称螺纹尺寸的3个交叉切槽。
- [ ] **`flange_nut` (法兰螺母)**
  - **标准:** DIN 6923 / ISO 4161
  - **核心逻辑:** 六角基体 + 查表生成的底部圆锥法兰。
- [ ] **`spring_pin` (弹性圆柱销)**
  - **标准:** ISO 8752 / DIN 1481
  - **核心逻辑:** 查表获取壁厚与缝隙宽度，考验薄壁和倒角生成的稳定性。
- [ ] **`pipe_plug` (螺纹堵头)**
  - **标准:** DIN 906 (内六角锥螺纹) / DIN 910 (外六角带法兰)
  - **核心逻辑:** 锥度/直圆柱特征提取，螺纹规格查表。
- [ ] **🔧 升级 `coil_spring` → 完整 DIN 2095 端面处理**
  - **现状:** 已 DIN 2095 wire 表 + medium 有平磨端。
  - **要补:** "两端并紧且磨平" (closed and ground ends)：末端 1–1.5 圈 pitch 收口至 wire_d，然后平面切除顶/底。
  - **不新开 family，改现有 `coil_spring.py` hard 档。**

#### 🔴 Phase 3: Hard (高难度，包含复杂扫掠、非线性计算与特殊曲线)
这类零件的脚本化最具挑战性，但对生成式 AI 学习复杂的 CAD 拓扑极具价值。

- [ ] **`disc_spring` (碟形弹簧)**
  - **标准:** DIN 2093
  - **核心逻辑:** 极其简单的外形，但内径、外径、厚度、自由高度之间是严格的非线性表驱动关系。
- [ ] **`spline_shaft` (单体花键轴)**
  - **标准:** DIN 5480
  - **核心逻辑:** 生成轴段单体，使用查表的模数、齿数、压力角生成高密度的渐开线 Profile 并拉伸。
- [ ] **`roller_chain` (滚子链，配对 sprocket)** ⭐ NEW
  - **标准:** ISO 606 (short-pitch transmission precision roller chains)
  - **核心逻辑:** 查表 pitch $p$、roller diameter $d_1$、inner width $b_1$、pin diameter $d_2$、plate height $h_2$（与 sprocket 共享同一 ISO 606 chain code，如 `06B`/`08B`/`10B`）。
  - **单元结构:** 一个 link = 两片 8 字形外板 + 两片内板 + 2 枚销 + 2 枚套筒 + 2 枚滚子；按 $N_{links}$ 沿直线 pattern 重复。
  - **难点:**
    1. 8 字形链板轮廓（两个圆弧 + 切线）的 polyline 生成。
    2. 内/外板交替（偶数索引外板、奇数索引内板），销与滚子同轴。
    3. 保持与现有 `sprocket` / `double_simplex_sprocket` 的 pitch 一致，形成可驱动组合。
  - **数据价值:** 周期性 pattern + 嵌套同轴圆柱 + 8 字 polyline = 对 sprocket 的完美补集。
