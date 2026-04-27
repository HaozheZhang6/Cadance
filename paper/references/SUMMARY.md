# Reference Digest — 9 Papers for BenchCAD NeurIPS 2026 D&B

**Read date:** 2026-04-24/25 · **Per-paper notes:** `notes/<slug>.md`

| 类别 | Paper | Venue | 核心贡献 (一句话) |
|---|---|---|---|
| CAD 直接竞品 | **Text2CAD** | NeurIPS'24 D&B | 660k 4-级 NL 标注 DeepCAD + BERT/AR Transformer 出 sketch-extrude token |
| CAD 直接竞品 | **CAD-Coder** | NeurIPS'25 main | 110K text→CadQuery + Qwen2.5-7B SFT+GRPO + CD reward |
| **MSU/SnT lineage I** | **CAD-Recode** | ICCV'25 | 1M procedural 训练点云→CadQuery,Qwen2-1.5B,DeepCAD/Fusion360/CC3D SOTA |
| **MSU/SnT lineage II** ⭐ | **cadrille** | **ICLR'26** | CAD-Recode v1.5 → Qwen2-VL-2B + pc/img/text 三模态统一 + Dr.CPPO online RL,DeepCAD img IoU 92.2 |
| **MSU/SnT lineage III** ⭐ | **CADEvolve** | arxiv'26.02 | cadrille pipeline + GPT-5-mini 进化数据扩到 2.7M scripts,DeepCAD img IoU 92.6 |
| CAD 直接竞品 | **CADCodeVerify (CADPrompt)** | ICLR'25 | 200 NL→CadQuery 专家 benchmark + VLM 自问自答 refine |
| D&B 结构标杆 | **Infinity-Chat (Hivemind)** | NeurIPS'25 best D&B | 26K real query + 31K human anno + 70+ LM,命名 "Artificial Hivemind" |
| D&B 结构标杆 | **MMSI-Bench** | ICLR'26 | 1000 全人工 multi-image MCQ + 11-task taxonomy + 37 MLLM,human gap 67% |
| D&B 结构标杆 | **AutoCodeBench** | ICLR'26 | 3920 multilingual code 题全自动合成 + Lite/Complete 双变体 + 30+ 模型 |
| Hanjie 协作风格 | SportR + SPORTU | ICLR'26 + ICLR'25 | benchmark + Qwen2.5-VL-7B SFT→GRPO,IoU 4.61→9.94,见 `notes/sportr_style.md` |

> ⚡ **MSU/SnT 三连发**(Russian/Luxembourg/Armenia 同 lab):CAD-Recode (Rukhovich 一作, ICCV'25)→ cadrille (Kolodiazhnyi 一作 + Rukhovich corresp, ICLR'26)→ CADEvolve (Elistratov, arxiv'26.02)— 实质一条 SFT+RL+evolutionary 数据管道的 3 个里程碑;**全部 release HF 模型权重 + 推理脚本**,可直接拉到 BenchCAD 上跑 transfer。

---

## 1. 跨篇 storyline 套路 (D&B 文章共有的 narrative DNA)

### 1.1 开篇 hook 三种模板
- **视觉冲击 figure** (Infinity-Chat 的 "time is a river" PCA;MMSI-Bench 的 4-panel headline)— 直接 demo 问题,reviewer 30 秒被说服。
- **一表压死 prior** (AutoCodeBench Table 1)—列出 6-7 个正交 axes (multilingual / human-free / balanced / multi-logic / 长 problem / 高难度),一格一格打 ✓/✗,prior benchmark 全 ✗ 我们全 ✓。
- **gap 三段式** (MMSI-Bench / Infinity-Chat 都用):existing 路线 1 不行 (e.g. 模板化) → 路线 2 不行 (e.g. subsplit 不专门) → 我们独占新空间。

### 1.2 Contribution 永远三件套
所有 4 篇 D&B paper 的 contribution 都是 (real/curated 数据 + 显式 taxonomy + 高质量 ground truth/anno) 或其变种。BenchCAD 完美映射:
- 20,143 verified parts (多源:Fusion360 + DeepCAD + 程序合成)
- 106-family taxonomy (3 维 × 多类型)
- 5-task evaluation harness + IoU≥0.99 verified GT (= machine-verified dense anno)

### 1.3 给现象起名 (sticky term)
- Infinity-Chat: **Artificial Hivemind** (intra+inter model homogeneity)
- MMSI-Bench: **scaling cliff** + **error type 4 类** (grounding / overlap-matching / situation-transformation / spatial-logic)
- AutoCodeBench: **upper bound 74.8 < 100** (远未饱和) + **multi-logic** axis

> BenchCAD 候选 sticky term (二选一定):
> - **Parametric Blindness** — model 能画图但不会出对的参数 / **Family Cliff** — 简单 family 80% 但难 family 30%
> - 必须给两个数字命名,reviewer 才记得住。

### 1.4 "堵死所有 escape route" punchline
MMSI-Bench 把 "scale model 不 work / CoT 不 work / visual prompt 不 work" 全堵死,逼出"需要 fundamental new direction" → reviewer 接受 narrative。
BenchCAD 应该实测并堵死:
- scaling SFT data 不够 (vs CAD-Coder 110K)
- 多 view 不够 (vs MMSI-Bench)
- finetune 现有 code-LM 不够 (vs CAD-Recode)
- → 推 parametric-aware 训练 / RL with geometric reward 的 future work

### 1.5 Pipeline 与 benchmark 解耦命名
AutoCodeBench (data) vs AutoCodeGen (pipeline) 是分两个 contribution。
BenchCAD 也可以拆:
- **CadGen** = family registry + procedural sampling + IoU 验证流水线
- **BenchCAD** = 数据集 + 5-task benchmark
- 这样 contribution 列表多一条,reviewer 觉得"工作量大"。

### 1.6 Lite / Complete 子集设计
AutoCodeBench Lite = 按"被多少 model 解出"反向选,保留区分度强的中等难度 → 新 model 评估快。
**强烈建议 BenchCAD 也做 Lite**:
- BenchCAD-Lite (~500 parts,106 family × ~5 stratified) 用于快速 leaderboard
- BenchCAD-Full (20143) 用于完整复现
- BenchCAD-Edit-Only / QA-Only 单任务子集

---

## 2. 表/图标准 layout (D&B reviewer default expectation)

| Asset | 模板 | 来源 paper |
|---|---|---|
| **Headline Figure 1** | 4-panel: 数据例子 + taxonomy 饼图 + SOTA bar w/ human 顶线 + 1-shot demo | MMSI-Bench, Infinity-Chat |
| **Taxonomy Figure 2** | 每 task / 类放 1 representative + Q + A + reasoning | MMSI-Bench |
| **Pipeline Figure 4** | 4 阶段竖排 + quality control 反馈环 | MMSI-Bench |
| **Comparison Table 1** | benchmark × axes (✓/✗ + 数字),最后一行是我们 | AutoCodeBench |
| **Main eval Table** | 行 = model (proprietary / open-source / baseline 三段) × 列 = sub-task,human 行铺底,bold per group best | MMSI-Bench, Infinity-Chat |
| **Multi-axis Table** | 行 = model × {reasoning/非}; 列 = 子集 + Avg; Count 行最上 + Upper bound 行 | AutoCodeBench |
| **Error analysis** | manual 4 类 + automated pipeline + stacked bar | MMSI-Bench |
| **Ablation 三表** | 训练量 / sampling / 架构维度分离 | CAD-Recode |

---

## 3. 关键 metric / 评测协议 trade-off

| Metric | 谁用 | BenchCAD 是否采用 | 备注 |
|---|---|---|---|
| **Mean / Median Chamfer Distance** | Text2CAD, CAD-Coder, CAD-Recode | **是** (CAD 圈标准) | ×10³ 量级习惯;失败惩罚 √3 |
| **3D IoU (rotation-invariant)** | CAD-Recode (普通 IoU) | **是 (rot-invariant 是我们独家)** | 强调与 CAD-Recode/CADCodeVerify 的 SE(3) 不变性差异 |
| **Invalidity Ratio (IR = exec fail rate)** | Text2CAD, CAD-Coder, CAD-Recode | **是** | 直接比较 |
| **Compile rate** | CADCodeVerify | **是** | 等价 1-IR |
| **Pass@1** | AutoCodeBench | **edit task 可用** | edit 任务可借 |
| **F1 (primitive type)** | Text2CAD | 可考虑 (feature-F1) | 我们已有 feature-F1 |
| **GPT-4V judge (二选一)** | Text2CAD | 可考虑 (LLM-as-judge baseline) | 4-view + Undecided 选项 |
| **Human / expert upper bound** | MMSI-Bench (97%) | **必须做** | 这是 D&B reviewer 的 hard requirement |
| **Best-of-N + min CD selection** | CAD-Recode | 可作为 inference 策略 ablation | 暴力提升 IR |

---

## 4. 各 CAD 竞品的逐一定位 (related work 行文用)

### Text2CAD [Khan et al., NeurIPS'24 D&B]
> 第一次为 DeepCAD 数据加 4 级 (abstract→expert) 自然语言标注并训练 BERT+AR Transformer 出 sketch-extrude token 序列;但其底层数据继承 DeepCAD 的 rect/cyl 偏置 + sketch+extrude 单一 op + token 序列不可执行,与 BenchCAD 的 106-family 程序化合成、CadQuery 可执行代码、5-task multi-modal benchmark 的定位正交。

### CAD-Coder [Guan et al., NeurIPS'25 main]
> 把 text→CAD 重新表述为 text→CadQuery,用 GRPO + CD reward 训练 Qwen2.5-7B,Mean CD 6.54 (4.5× 优于 Text2CAD);但训练数据仍由 LLM 反向合成自 Text2CAD/DeepCAD 底库 (sketch+extrude bias),且只评单一 text→CAD 任务,与 BenchCAD 程序化合成的 106-family 数据 + 5-task multi-modal benchmark (含图像和编辑) 互补。

### CAD-Recode [Rukhovich et al., ICCV'25]
> 首次将 pre-trained LLM (Qwen2-1.5B) 用于 point-cloud → CadQuery 反向工程,1M procedural 训练集刷新 DeepCAD/Fusion360/CC3D SOTA;但仅覆盖 sketch-extrude、本质是训练 corpus 无 verification 协议、亦无 image-conditioned 或 edit/QA 任务的 held-out benchmark — BenchCAD 在覆盖广度 (106 families × 多操作)、verified IoU≥0.99 评测集、5-task 多模态评测协议三方面互补。

### CADCodeVerify (CADPrompt) [Alrashedy et al., ICLR'25]
> 提出首个 CAD code-generation 定量 benchmark CADPrompt (200 NL prompts + 专家 CadQuery 代码) 并以 VLM 自问自答视觉验证作 refinement,提升 GPT-4 PCD 7.3% / compile 5.5% — 但规模仅 200 例、无 family 结构、IoGT 基于 bbox 且 prompt 含绝对几何;BenchCAD 在 verified 规模 (×100)、family 化参数生成 (106 families)、rotation-invariant IoU、5-task 多模态评测协议方面进一步推进 CAD code 评测基础设施。

---

## 5. BenchCAD 必须正面回应的 challenges (审稿人会问)

**审稿人会问 1:** "你 20K verified vs CAD-Recode 1M / Text2CAD 660K text 标注,凭什么够?"
答案: 我们是 *evaluation set* 不是 training corpus,目标衡量模型而非训模型;另提供 162K GenCAD pairs 给训练。

**审稿人会问 2:** "CADPrompt (200) 已经在 ICLR'25 是 CAD code benchmark,为何不用它评?"
答案: 太小、无 family 结构、prompt 含绝对几何 (违反 scale invariance)、IoGT 基于 bbox 不是 mesh-level rotation invariant。

**审稿人会问 3:** "CAD-Coder 已经做了 text→CadQuery + RL,你们 task 重叠?"
答案: 我们 task 是 *image*→CadQuery (img2cq),不是 text→CadQuery,且我们多 4 个新 task (qa_img/qa_code/edit_img/edit_code);CAD-Coder 是 model paper,我们是 dataset+benchmark paper 互补。

**审稿人会问 4:** "你们 106 families 是不是合成偏置太重?vs DeepCAD 真实工业件多样性差?"
答案: (a) 我们 family 来自 ISO/DIN 标准件 + 实际工程组件 (扎根真实);(b) 程序化保证 coverage 可控且可平衡 (DeepCAD 自己 imbalance 偏 rect/cyl);(c) CAD-Recode 已证明 procedural > real (Table 3);(d) 我们另含 verified Fusion360 + DeepCAD 子集兜底。

**审稿人会问 5:** "human upper bound 在哪?" (MMSI-Bench / Infinity-Chat 都有 dense human anno)
答案: 必须做 — expert CadQuery 工程师对 ~50 sample/task 给 ground truth answer,作为 oracle ceiling。**TODO: 补这块实验。**

**审稿人会问 6:** "scaling 实验做了没?" (MMSI-Bench, AutoCodeBench 都做)
答案: 必须测同 family model series (e.g. Qwen2.5 0.5B/1.5B/7B/32B/72B) 看 scaling cliff,如果 scaling 不 work 即是第二 punch line。

---

## 6. BenchCAD Intro 更新 checklist (基于以上 digest)

- [ ] 加 sticky term ("Parametric Blindness" 或 "Family Cliff",二选一 + 给定义数字)
- [ ] 加 "block all escape routes" framing (scaling / multi-view / finetune 都不够)
- [ ] 在 contribution list 提 Lite / Full / single-task subset 设计
- [ ] 把 "CadGen pipeline" 单列为 contribution 1 (vs benchmark 是 contribution 2/3)
- [ ] 必须正面引用并区分 CAD-Coder + CAD-Recode + Text2CAD + CADCodeVerify (4 段一句话定位见 §4)
- [ ] human / expert upper bound 实验 (TODO 补)
- [ ] scaling cliff 实验 (TODO 补)
- [ ] 做 headline 4-panel figure 1 草图 + 一表压死 (BenchCAD vs CADPrompt vs CAD-Recode vs Text2CAD vs CAD-Coder × 7 axes)

---

## 7. Open questions (留给下一轮)

- 我们的 sticky term 选哪个? "Parametric Blindness" / "Family Cliff" / "Visual-fidelity gap"
- CadGen 单独命名是否 oversell? 还是合并入 dataset section
- BenchCAD-Lite 怎么选 subset? 按 model pass-rate 反向 (AutoCodeBench 套路) 还是按 family 难度均衡
- 是否要做 MMSI-Bench 式 11-task taxonomy 矩阵图 (input modality × output modality × 推理深度)
- 是否要 expert upper bound — 工时贵但必须有
- arXiv preprint 现在挂还是录取后挂 (会影响双盲)
