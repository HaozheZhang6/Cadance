# MMSI-Bench: Multi-Image Spatial Intelligence (ICLR 2026)

**arXiv:** 2505.23764 · **Authors:** Sihan Yang, Runsen Xu et al. (Shanghai AI Lab + CUHK + 多校) · **Code:** https://runsenxu.com/projects/MMSI_Bench
**One-line:** 1000 道纯人工标注 multi-image MCQ + 11-task taxonomy,37 个 MLLM 全跑,human 97% vs SOTA 41% — 史上最大 spatial intelligence human-model gap。

## 1. Storyline (作者讲的故事 — 重点!这是我们要学的)
极标准的 D&B benchmark narrative。开篇 hook = "spatial intelligence 是 embodied AGI 必经之路,但现有 benchmark 全是 single-image,踩不到 real-world 痛点"。叙事三拍:(i) gap = 已有 multi-image benchmark 要么是 templated/auto-generated(VSI-Bench, MMIU)diversity 受限,要么是 BLINK / MuirBench 里 spatial 只是 subsplit;唯一 human-curated 的 ERQA 只有 113 multi-image。(ii) contribution = **完全人工** 1000 题 + **11-task taxonomy**(Position × 6 + Attribute × 2 + Motion × 2 + MSR)+ 每题 step-by-step reasoning(双重作用:质控 + automated error analysis)+ 6 名 3D-vision researcher × 300+ 小时 × 120K candidate images。(iii) punch line = **97% human vs 41% GPT-5 vs 30% best open-source = 史上最大 gap**;且 **scaling model size 几乎不 work**(78B vs 1B 只差 1.5%);CoT prompting 也不 work — 把所有"显然能 work"的常规招都堵死,逼出"需要 architectural / data 革新"结论。叙事最妙:每个发现都对应一个明确 "future work direction",reviewer 看完直接知道 "下一篇 paper 该解什么"。Error analysis 是结构上的双 punch — 既给 4 类 named error type,又给 automated pipeline 复用 reasoning anno。

## 2. Claim 链条 (各段论证)
- §1 Intro: 标准 4 段 — embodied AGI → spatial intelligence 必备 → existing benchmark 全单图 / 模板化 → MMSI-Bench 入场。每段最后一句都有 transition 句承上启下。结尾段直接 spoiler 4 个 error type,读者知道后面 §5 要展开。
- §2 Related: 两块 — multi-image VQA / spatial intelligence;每块逐 benchmark 点名(BLINK / MuirBench / VSI-Bench / ERQA)+ 一句话定位"它做了 X, 但缺 Y, 而我们 Z"。
- §3 MMSI-Bench: §3.1 是 11-task taxonomy(基于 3 元素 camera/object/region × 3 维度 position/attribute/motion + MSR 顶层),Table 1 是干净的 main-cat × sub-cat × description 三列;Figure 2 每 task 一个 representative 例子(图 + Q + A + reasoning)。§3.2 4 步 pipeline:数据采集 (8 dataset, 231 scenario, 12K image) → 标注 (6 researcher, free-form, 4-option MCQ, 必须需要≥2 image, 必须有 reasoning) → 质控 (3 reviewer 独立 audit) → difficulty(human answering time)。
- §4 Eval: 37 model + 3 baseline (random / human / blind GPT-4o);Table 3 是核心 — 11 column × 37 row,proprietary / open-source / baseline 分组,human level 行铺底。4 个 finding 直接列:(a) 全 model 接近 random;(b) open-source < proprietary; (c) MSR + camera motion 最差;(d) **scaling 不 work**。§4.3 进一步:CoT / visual prompting 也救不了。
- §5 Error Analysis: §5.1 manual 4 类 (grounding / overlap-matching / situation-transformation / spatial-logic),每类配 figure 例子;§5.2 automated pipeline — 给 model 正确答案 + reasoning,让它自评 error type,准确率 53% → 78%(证明 reasoning anno 不可替代),scale 到全 benchmark 给 error 分布柱状图。
- §6 Conclusion: 短小 — 复述 contribution + future direction。

## 3. 关键佐证 (具体数字)
- 1,000 questions / 1,990 unique images / avg 2.55 image per Q / max 10 image
- 8 data sources (ScanNet, nuScenes, Matterport3D, Ego4D, AgiBot-World, DTU, DAVIS 2017, Waymo) / 231 scenarios / 12K image pool
- 11 task categories (10 atomic + 1 multi-step)
- 6 researchers × 300+ hours × 120K candidate images inspected
- 37 MLLMs evaluated (proprietary + open-source) + 3 baselines
- Human level: 97.2%; GPT-5: 41.9%; o3: 41.0%; best open-source Qwen2.5-VL-72B: 30.7%; random: 25%; blind GPT-4o: 22.7%
- Scaling cliff: Qwen2.5-VL-72B vs 32B = +3%; InternVL3-78B vs 1B = +1.5%
- NVILA-15B 超过大多数 70B+ 模型 — 数据 > 参数
- CoT 只对 GPT-4o 有 modest gain,其他模型反而掉点
- Automated error analysis: 给 GT answer 53% → +reasoning anno 78%
- Avg question length 130 字符 / avg reasoning 253 字符

## 4. 对 BenchCAD 的启发 (重点是 narrative structure!)
- **storyline 套路可偷:**
  (1) **3-element × 3-dim taxonomy** 套路 — 他们 (camera/object/region) × (position/attribute/motion) 推出 10 个 atomic + 1 个 MSR。BenchCAD 应该模仿:把 5-task 用同样的二维(input × output 模态 / 推理深度)矩阵化,reviewer 一眼看到 "这是 systematic coverage 不是 ad-hoc 凑数"。
  (2) **"全人工标注" 当卖点** — 他们反复强调 "6 researchers × 300+ hours × not templated",对比 templated benchmark — 我们对应可以强调 "20,143 parts × IoU≥0.99 verified × 106 family covering X 工业领域",把 verification rigor 做成 contribution。
  (3) **"堵死所有 escape route"** narrative — scale model 不 work、CoT 不 work、visual prompt 也不 work,把读者所有 "也许这样就能 fix" 的退路堵死,逼出 "需要 fundamental new direction" — BenchCAD 应该:scaling SFT data 不够 / 单纯多 view 不够 / 简单 finetune 现有 code-LM 不够,需要 parametric-aware 训练。
  (4) **"reasoning annotation 双用途"** — 既用于质控也用于 automated error analysis。BenchCAD 的 verified GT (CadQuery code + STEP + 4 view) 等价多用途资产,应该明确说出 "这套 GT 让 5 个 task 共享一份数据"。
- **table / figure 套路可偷:**
  - Figure 1 = 4 panel 头图:左 task 例子 + 中 error 饼图 + 右 model bar(横轴 model 纵轴 acc, human 虚线在顶部)— 一张图 sell 数据多样性 + 难度 + gap。BenchCAD 等价:左放 1 个 part 的 4 view + GT code + 5-task QA 例子 + 中放 family 分布饼图 + 右放 SOTA bar 图带 human/oracle 顶线。
  - Figure 2 = 每 task 一个 representative,横向 3 列 × 多行 grid。BenchCAD 应该每 task / 每难度等级各放一个 example。
  - Table 1 = taxonomy 表(main-cat | sub-cat | description),极简洁。
  - Table 3 = 大评测表 — proprietary 块 / open-source 块 / baseline 块,human level 在最下铺底,column 是 fine-grained sub-task,**bold 标 best per group**。这是 D&B reviewer 的 default expectation,我们必须照做。
  - Figure 4 = pipeline 图(4 阶段竖排带子任务 icon + quality control 反馈环),让 reviewer 一眼信服 rigor。
  - Figure 6 + 7 = error analysis qualitative example + 各 model error 分布 stacked bar。
- **D&B "punch-line finding" 套路:**
  他们最炸的 punch line 是 **"97 vs 30 = 67% human-model gap, the largest among existing spatial benchmarks"** — 单数字直接成 headline。次炸点:**"scaling 不 work — 78B 比 1B 只多 1.5%, NVILA-15B 反超 70B+"** — 暗示数据 > 参数,直接 hook 数据界。BenchCAD 等价 punch line 候选:
  (a) **"Largest part-fidelity gap" — humans / oracle vs SOTA 在 IoU/参数准确率上的差**(若我们能算 human upper bound 就 pin 死);
  (b) **"Family Cliff" — easy family >X%, hard family <Y%, 落差 Z 倍 — 揭示 LM 不会参数化推理只会 pattern-match**;
  (c) **"Scaling-blind"** — 类比 MMSI-Bench,我们应该测大小 model series 看 scaling 是否 work,如果不 work 就成第 2 个 punch。
  推荐选 (b) 当 sticky 命名 punch + (c) 当结构性 punch,因为这两个能跨 task 复现。
- **structural 标杆:**
  D&B reviewer 用这篇 paper 反推 hard requirement: (i) ≥**1000 sample 量级**(他们 1K, Infinity-Chat 26K — 我们 20K 完全达标);(ii) **多源数据**(他们 8 dataset, 我们 Fusion360 + DeepCAD 已经 ≥2);(iii) **明确 taxonomy 且每类都有 example + 占比**;(iv) **≥30 个 model 大规模评测**(我们必须凑足);(v) **human / oracle baseline**(MMSI-Bench 的 97% human 是杀手锏,BenchCAD 必须要有 human/expert baseline 或 oracle ceiling);(vi) **error type 化 + qualitative example**;(vii) **automated error pipeline**(可复用 reasoning anno);(viii) **futuredirection 明确**(他们 future work 段落写"data quality > model size,需 architecture 革新")。

## 5. 一句话评价 (放在我们 paper 哪里 / 是否引用)
Must-cite,放 Related Work 的 "domain-specific multimodal benchmark / human-curated benchmark methodology" 段;Intro 里也可以一句话点名,作为 "近期 ICLR D&B 范本,通过 11-task taxonomy + 37 model + human gap 揭示 spatial intelligence bottleneck,我们采纳同样的 taxonomy-driven + scaling-cliff narrative 应用于 parametric CAD"。是 BenchCAD 在结构上**最像**的对照 paper,可以直接照 layout 写,reviewer 接受度高。
