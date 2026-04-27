# AutoCodeBench (ICLR 2026)

**arXiv:** 2508.09101 (v1, 2025-08-12) · **First author:** Jason Chou & Ao Liu (equal, Tencent Hunyuan) · **Code:** Homepage 链接 + 开源 multilingual sandbox(支持 20+ 语言)
**One-line:** 用 LLM-Sandbox 交互全自动合成 3920 道、20 种语言、无人工标注的高难度 multilingual code-gen benchmark,配套 Lite + Complete 两个变体评 30+ LLM。

## 1. Storyline
痛点:现有 code benchmark 要么 Python only(HumanEval/MBPP/LiveCodeBench),要么虽 multilingual 但靠手标且语言分布不均(MultiPL-E/McEval/FullStackBench),难同时兼顾难度+多语言+balanced。提出 **AutoCodeGen**: 反向流程,先从 Stack-Edu 真实代码 seed → LLM 生 self-contained solution + test input,沙箱执行拿 output → 拼回成 test function → 再倒推生 problem 描述,最后三段 filter (难度/质量/多样性)。配 multilingual sandbox 跑执行验证。产出 **AutoCodeBench (3920 题)** + **Lite (1586 题,放大模型差距)** + **Complete (1000 题,3-shot 评 base 模型)**。punchline: 即使 Claude Opus 4 (think) 也只 52.4 平均 Pass@1,而所有模型并集 upper bound 仅 74.8 → 远未饱和。

## 2. Section-by-section claim chain
- **§1 Intro:** 表 1 一表证明 ACB 同时满足 MultiLingual + MultiLogic + Human-Free + Balanced + 高难度,且 Problem Length (498.2) 远超 BigCode/MBPP/Live。四点贡献: AutoCodeGen 流程 / ACB 数据集 / multilingual sandbox / 30+ 模型实验。
- **§2 (合并 Method+Stats):** 2.1 数据概览 (60% hard,平均 9.6 test cases,14 categories,20 languages 均衡);2.2 流程 4 步 (Solution Gen / Test Gen / Problem Gen / Filtering)+approx language translation (低资源语言用翻译扩);2.2.6 Lite 用 pass count 升序去掉<2 pass 的题,选~1500 中等难度题。
- **§3 Experiments:** 30+ 模型,Pass@1 主指标。子分析: 主表 (4)、Lite (5)、popular vs low-resource (Fig 3)、multi-logic (Fig 4)、参数+sampling scaling (Fig 5)、multi-turn refinement w/ sandbox feedback (Fig 6)、Complete base 模型表 (6)。
- **§4 Further Discussion:** 6 名标注员人工验证 6 种语言,87.6% accuracy 证流程靠谱。Bias 分析: 故意只用 DeepSeek 系做 gen+critic,但用 DeepSeek-Coder-V2-Lite 做难度 filter 形成 push-pull → Table 7 显示 bias 影响 minimal。
- **§5 Related work:** 两节: Code Gen Benchmarks (HumanEval → LiveCodeBench → McEval/FullStackBench,共同点都是 manual curation) + Code Data Synthesis (Evol-Instruct / OSS-Instruct / KodCode 都做训练数据,我们扩到 benchmark)。
- **§6 Conclusion:** 重述贡献,呼吁社区关注 multi-logic + 低资源语言。

## 3. Key numbers
- 3920 problems / 20 languages / 14 categories / 37,777 test cases / avg 498.2 char/题 / 9.6 test/题。
- Lite: 1586 题 / 15,341 tests; Complete: 1000 题 (50/语言)。
- 难度分布 ACB: 646 easy / 846 med / 2428 hard (60%+ hard);Lite: 263/421/902。
- 难度由 DeepSeek-Coder-V2-Lite 10 次采样定: 0 通过 = hard, 1-5 = med, >5 = easy。Python 上过滤掉 25.1% 太简单题。
- 主表 SOTA: Claude Opus 4 (Think) 52.4 平均 Pass@1; o3-high/Sonnet4 51.1; current upper bound 74.8。
- Lite: Claude Opus 4 (Think) 64.5; upper bound 100。
- 87.6% 人工验证准确率(6 语言抽样);bias 实验 3600 数据点 6 语言。
- Multi-logic 子集 1622 题,所有模型掉 3-5 点。
- Multi-turn refinement w/ sandbox: DeepSeek-V3 三轮 48.1 → 59.7;Qwen2.5-Coder-32B 35.8 → 47.4。
- 评 30+ 模型,size 1.5B-1T,reasoning + non-reasoning 两栏对照。

## 4. Takeaways for BenchCAD
- **Storyline tricks worth borrowing:** 一表压制(Table 1 用 6-7 列布尔/数字直接打死所有 prior benchmark);用 "human-free" + "balanced" + "multi-logic" 等正交 axes 重定义"我们独有"。最后强调 upper bound 74.8 < 100 暗示 benchmark 远未饱和 → 我们也可秀 4-task aggregate score 上限 + 当前最佳差距。
- **Multi-axis result-table layout to learn from:** Table 4/5 = 列 = 20 个语言 + Average,行 = 30+ 模型 × {Reasoning / Non-Reasoning} 两块。我们可改成 列 = 106 families 或 family group + Average,行 = 模型 × {易/中/难} 或 {img2cq/edit/qa}。Count 行 (题数) 放最上 + Current Upper Bound 行作 reference 是好招。
- **How they frame "automated construction" as methodology:** 把 pipeline 自身命名 (AutoCodeGen) 与产出 benchmark (AutoCodeBench) 解绑,贡献清单第 1 条就是流程 → 我们 BenchCAD 的 family registry + procedural sampling + IoU 验证流程也应单独命名(eg. CadGen)成第一贡献,数据集 + 5-task suite 作第二/三。
- **"Lite" / "Complete" split design — should we adopt?:** **强烈建议借鉴**。Lite = 按"被多少模型解出"反向选,刻意保留区分度强的中等难度题 → 评新模型快、leaderboard 差距大。Complete = 抽 1000 题 (50/语言) 配 3-shot 给 base 模型 → 与 instruct 评测分离。我们的对应物: BenchCAD-Lite (~500 高区分度 parts,5 families × 100) 用于快速排榜;BenchCAD-Edit-Only / BenchCAD-QA-Only 子集允许只评单任务。
- **Their strengths we must acknowledge in our related work:** (1) full pipeline 全自动 + 沙箱执行验证;(2) 真正 balanced multilingual (20 语言每个 ~200 题);(3) 配套 87.6% 人工验证 + 显式 bias 分析章节(我们也该加 family-level bias 分析);(4) multi-turn sandbox refinement 实验结构清晰可借;(5) Complete 这种 base-model 子集是 niche 但 useful 的设计点。

## 5. Single-sentence citation framing
AutoCodeBench [Chou et al., ICLR 2026] 通过 LLM-sandbox 交互全自动合成 3920 道 20 语言 code-gen 题,验证了 sandbox-verified、execution-grounded benchmark 在覆盖度和难度上可超越人工标注流水线 — BenchCAD 把这一思路从纯文本代码扩展到 parametric CAD 的几何世界,用 IoU≥0.99 的执行验证 + 106 families × 5 任务实现同样的 human-free + multi-axis 评测。
