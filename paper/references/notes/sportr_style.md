# Hanjie Chen 写作 style 分析 (基于 SportR ICLR'26 + SPORTU ICLR'25)

## 0. Meta info
- **SportR** arxiv 2511.06499v3 (Mar 2026), ICLR 2026 接收。作者列表:Haotian Xia¹*, Haonan Ge³*, Junbo Zou⁴*, ...(约 14 人,3 名 equal contrib)... Vicente Ordonez¹², Weining Shen³, **Hanjie Chen¹²**(末位)。Hanjie 在 Rice CS。
- **SPORTU** arxiv 2410.08474v4 (Mar 2025),ICLR 2025。作者:Haotian Xia¹²*, ...(13 人)... Weining Shen², **Hanjie Chen¹**(末位)。
- **Hanjie 的角色**:典型 senior advisor / framing person。两篇都是末位通讯,corresponding email 含 hanjie@rice.edu。她不写 ablation,但负责 storyline、taxonomy、contribution 列表、abstract。两篇的 framing 句式高度一致 → 是她的 voice。

## 1. Storyline 套路 (intro 怎么开)
SportR intro 4 段 + contribution 块:
- §1 段:**领域宏观钩子**(sports → AI applications),3-5 句,引 4-5 cite 铺背景,结尾用一个**具体小例子**收紧("correctly adjudicating a subtle hand-check foul in basketball demands not only recognizing the interaction but also...")。
- §2 段:**金字塔三层 framing**(perceptual / 中间 fundamental / elite),明确把自己定位在中层。这是她标志性手法 —— 用一个**视觉化 metaphor**(pyramid)+ 三层切分。
- §3 段:**QA 范式回顾 + gap 列举**,排比"While X..., Conversely Y..., Furthermore..."把 prior work 的不足列 3 条。
- §4 段:"To address these critical gaps, we introduce SportR..." + 数据规模数字。
- **Contribution 块:3 条编号 list**(threefold)。

直接 quote 听 voice:
> "Deeply understanding sports requires an intricate blend of fine-grained visual perception and rule-based reasoning—a challenge that pushes the limits of current multimodal models."(abstract,典型 X requires Y blend of A and B 句式)
> "However, the most critical and immediate challenge lies somewhere in the middle: Mastering the identification of fundamental and common fouls and tactics..."(冒号 + 强调中层)

SPORTU intro 同结构:领域宏观→应用举例→prior gap 排比→"To address this gap, we introduce SPORTU"。**完全延续。**

## 2. 段落结构与节奏
- **段长中等**:平均 5-8 句,intro 段 ~120-180 词。不喜欢一句段也不喜欢超长段。
- **段首句 = thesis statement**,几乎 100%。"To address...", "Our design prioritizes...", "A key feature of...", "The cornerstone of our work is..."。
- **重 we,轻 passive**。"we introduce / we focus / we conducted / we observe" 高频。"We" 出现密度 ~每 30-40 词一次。
- **句长偏长**,常用破折号插语 + 冒号引列表。例:
  > "We focus on a diverse set of five globally popular ball and racket sports – basketball, soccer, table tennis, badminton, and American football – to provide a rich testbed for generalization."
  > "At its base lies perceptual understanding—recognizing players, actions, and basic game states."
  长句 + 短结句混合;偶尔短句砸结论:"This is a domain where, as we will demonstrate in our experiments, even the most advanced MLLMs struggle profoundly."

## 3. Contribution 列表习惯
- **编号 bullets**(1./2./3.),不用 "•"。
- **3 条**(threefold)。SPORTU 同样 3 条左右。**不超 4 条**。
- 每条 4-7 行,**不是一行短句**,带细节和数字。
- 都带具体数字(50 fouls / 12 tactics / 6841 CoT / IoU 4.61→9.94%)。
- 动词开头模式:`We introduce / We introduce / We demonstrate`(一句话:1+2 是建什么,3 是 demo 出什么 finding)。

## 4. Section 结构 (主 paper 10 页)
| § | 标题 | 估页 | 权重 |
|---|---|---|---|
| 1 | Introduction | ~1.3 p | 中 |
| 2 | Related Work (2.1+2.2) | ~1.3 p | 轻 |
| 3 | SportR Benchmark (3.1 QC + 3.2 Image + 3.3 Video) | ~3 p | **最重** |
| 4 | Experiment (4.1 baseline + 4.1.1 training + 4.2 eval) | ~1.3 p | 中 |
| 5 | Result (5.1 image + 5.2 video + 5.3 error) | ~2 p | 重 |
| 6 | Conclusion | ~0.5 p | 轻 |
- **Dataset 章是绝对中心**(~30% 篇幅),Quality Control 是单独 subsection。
- **没有独立 Discussion / Limitations / Ethics / Broader Impact 章**。Limitations 散在各 subsection 末尾(如"While this is an important avenue for future research, our focus...")。
- §5.3 Error Analysis 是**reviewer feedback 加的**(标题里直接写),说明原稿可能更短 → 她对 rebuttal 反馈很 responsive。

## 5. Table / Figure 风格
- **2 个 figure + 2 个 table** 在主 paper(+1 error pie fig)。极简。
- **Table 是密集型**:model × Q1-Q7 grid,每个 cell 一个百分数,加粗最高。
- **Figure 1/2 是 taxonomy + sample 拼图**(50 类 + QA 例子);**Figure 3 是 error pie**。**没有定量曲线图**(no scaling curve, no loss plot)。
- **Caption 中等长度**(2-4 句),**带 takeaway**:"The analysis reveals that Visual Perception Error is the most common issue, followed by Hallucination Error."

## 6. Punch line / sticky term 用法
- **没有命名 finding**(无 Hivemind 类术语)。
- 最 sticky 的术语是**"progressive QA hierarchy" + "pyramid of sports understanding"** —— 整篇反复出现 ≥6 次,abstract、intro、§3 都点。
- 主 finding sell 法:**用具体百分数对比**+**强调 still struggle**。例:"only improving from 4.61% to 9.94% on average IoU, highlighting the difficulty"。**bold 表格最高分,但正文不 bold**。
- 标志性结论句式:"X remain modest, suggesting that the core challenge of Y is far from solved." / "presents a profound challenge to current models"。

## 7. Limitations / Discussion / Ethics 处理
- **不单列**。limitations 用"While X is an important avenue for future research, our focus is..." 句式包装成 future work,**藏在 dataset 章**(§3.3 末)。
- **没有独立 Ethics / Broader Impact 节**。SPORTU 只在 conclusion 末尾一句"We also discuss the broader impacts of our findings in Appendix B"打发。
- **自承认弱点 ≈ 30%、包装为 future work ≈ 70%**。
- Acknowledgments 一段,2 句,提资助 + 致谢 reviewer。

## 8. 引用风格
- 引用密度高:intro 每段 4-8 cite,related work 段 8-12 cite。
- **多 cite per claim** 是常态:"(Xia et al., 2022; Oved et al., 2020)" / "(OpenAI, 2024b; AmazonAGI et al., 2025; Gemini Team, 2024; Anthropic, 2024a)"。
- **主动比较 prior**:related work 每写一个 prior 都点出**它的具体短板**("provides explanations for evaluation, their annotations are not in the form of fine-grained CoT"),不只是列名。
- 她**不点已被取代的旧范式**,只点能直接对比的同类工作。

## 9. 对 BenchCAD 写作的 5 条具体建议 (actionable)
1. **Contribution 写 3 条,不要 5 条。** 当前 draft 若是 5 task = 5 contribution,合并成"(1) 我们建 benchmark 含 5 task + capability decomposition; (2) 我们引入 X 独特资源 (e.g. parametric program GT / multi-view); (3) 我们做 SFT/eval demo 出 finding Z"。每条 4-7 行带数字。
2. **Intro 第二段塞一个金字塔 / 层级 metaphor**。她的 SportR pyramid (perception / fundamental / elite) 直接对应 BenchCAD 可设:primitive → composition → parametric reasoning → constraint solving。让审稿人记住一张图。
3. **Intro 第一段结尾用一个具体 example,不要泛述。** 如:"correctly generating a parametric flange with M8 bolt-circle requires not only sketching the profile but also..."。
4. **不要单列 Discussion / Limitations 章**。把 limitations 嵌进每个 task subsection 末尾,用"While X remains an important direction, our focus..."句式。Ethics 走 appendix 一段。
5. **Tables 走密集 model×task grid,Figures 只放 taxonomy 拼图 + 1 张 error/breakdown 饼**。不要画 loss curve / scaling 图。Caption 必带一句 takeaway。**bonus**:bold 最高分,正文别 bold。

## 10. 一句话总结她的写作 voice
**Authoritative-but-modest senior advisor:用 pyramid/层级 framing 把领域切成"已解决 / 我们的中层 / 留给未来",contribution 三条编号、abstract 数字密集、limitations 包装成 future work,正文 we 主导、长句加破折号插语、段首必 thesis,关键动词永远是 introduce / focus / demonstrate / highlight。**
