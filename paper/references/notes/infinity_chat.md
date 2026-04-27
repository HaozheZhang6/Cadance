# Infinity-Chat / Artificial Hivemind (NeurIPS 2025 D&B Best Paper)

**arXiv:** 2510.22954 · **Authors:** Liwei Jiang et al. (UW, AI2, CMU, Stanford, Lila, SynthLabs) · **Code:** https://github.com/liweijiang/artificial-hivemind
**One-line:** 26K 真实世界 open-ended queries + 31K dense human anno + 70+ LM 评测,首次系统揭示 LM 在开放式生成中的 "Artificial Hivemind"(同质化)效应。

## 1. Storyline (作者讲的故事 — 重点!这是我们要学的)
开篇 hook 极猛:Figure 1 直接放 25 个 LM 写 "time is a metaphor",PCA 一打全聚成 "time is a river" + "time is a weaver" 两簇 — 视觉冲击立刻让 reviewer 信服 "homogenization 是真的"。然后 narrative 三段式:(i) gap = 已有 diversity 评测全是 narrow synthetic task(随机数/名字/诗),无法 capture 真实用户多样性;(ii) contribution = 三件套 — 大规模真实 query (26K) + 首个 open-ended 分类法 (6/17) + 密集人工 anno (25/example) 同时拿到 absolute rating + pairwise preference;(iii) punch-line = 命名 "Artificial Hivemind" = intra-model repetition + inter-model homogeneity(更猛的是后者)。叙事最妙:每一段都用一个**命名 phenomenon** 锁死 takeaway(Hivemind / mode collapse / 25-annotator distribution / 散点图相似性)。结尾 frame 成 long-term AI safety risk(homogenization of human thought)— 拉高 stakes,直接对接 NeurIPS reviewer 的政策关注。

## 2. Claim 链条 (各段论证)
- §1 Intro: hook = LM 在 open-ended 任务失败 → cause 长期同质化担忧 → 现有 benchmark 局限 (narrow,synthetic) → 我们提出 Infinity-Chat → 30 行内就把 (data, taxonomy, hivemind, 31K anno) 4 个 contribution 报清楚。
- §2 Infinity-Chat 数据: WildChat 37K filter → 26,070 open-ended queries; 半自动 taxonomy(100 seed 人工标 → GPT-4o scale)→ 6 top-cat / 17 sub-cat + 314 novel cat (word cloud)。每 cat 给百分比和真实 query 例子。
- §3 Hivemind 实证: 用 100 query subset (Infinity-Chat 100); intra-model 25 model × 50 sample/query; 79% query 内部 sim>0.8;min-p decoding 也救不了(81% 仍 >0.7);inter-model 相似度 71-82%,DeepSeek-V3 vs GPT-4o sim=0.81;给 verbatim phrase overlap 例子(iPhone case 文案、social media motto 一字不差)。
- §4 RM/Judge calibration: 31,250 human anno (25 anno × 15 resp × 50 prompt 绝对 rating + 25 × 10 × 50 pairwise);用 Tukey fence 切 "similar-quality" subset、用 Shannon entropy 切 "disagreed" subset;发现 LM/RM/Judge 与 human 的 Spearman 在这两个 subset 上**显著掉**。
- §5 Related: 三块 — diversity collapse / creativity 评测 / pluralistic alignment;每块两三句标准定位。
- §6 Conclusion: 简短 — 重复命名 "Artificial Hivemind"、抛 future work hook(pretrain data? alignment? contamination?)。

## 3. 关键佐证 (具体数字)
- 26,070 open-ended + 8,817 closed-ended queries (mined from WildChat 37,426)
- 6 top-level / 17 fine-grained taxonomy + 314 novel categories
- 70+ LM 评测,主文报 25 个
- 31,250 human anno;每 example 25 anno (vs HelpSteer3 只有 3)
- Intra-model: 79% query 内 avg pairwise sim > 0.8 (top-p=0.9, t=1.0)
- Min-p (t=2.0): 81% > 0.7,61.2% > 0.8 — 仍同质
- Inter-model: avg sim 71-82%,DeepSeek-V3 vs Qwen-max sim=0.82
- N=50 top-similar 集中平均来自 ~8 个不同 model(应该全来自 1 个才正常)
- RM/Judge 评测面: 56 LMs + 6 reward models + 4 LM judges
- "Time is a river" / "time is a weaver" — 25 model × 50 sample 全部聚 2 簇

## 4. 对 BenchCAD 的启发 (重点是 narrative structure!)
- **storyline 套路可偷:**
  (1) 开篇用一个**视觉冲击 figure**直接 demo 问题(他们是 "time is a river" PCA 散点)— 我们对应可以做:同一个 CAD prompt 给 8 个主流 model,展示生成 STEP 的 IoU/视图全跑偏 → 直观告诉 reviewer "现有 model 不会做参数化 CAD"。
  (2) Contribution 三件套结构:**真实数据 + 显式分类法 + 密集 ground truth** — BenchCAD 完美对应:20,143 verified parts + 106 family taxonomy + 5-task benchmark。把 contribution 永远以三件套 sell。
  (3) 给现象**起一个名字**(Artificial Hivemind)成 sticky term — BenchCAD 应该给我们的核心发现起名,比如 "Parametric Blindness"(model 能画但不会参数化)或 "Family Cliff"(简单 family 80% 但难 family 30%)。
  (4) 把 contribution frame 成 long-term risk / safety / progress north-star,而不只是 "我们做了个数据集"。
- **table / figure 套路可偷:**
  Figure 1 = headline qualitative demo(同 prompt,N 个 model,聚类 / overlap 一目了然);Figure 2 = taxonomy hierarchy + 每 cat 真实 query 例子 + 占比百分比(我们应该照搬:106 family 分组,每组放 representative part + 占比 + 难度分布);Figure 4-5 heatmap = sim 分布的 binning(quantitative 跟随 qualitative)。Table 永远是 25 model × N task 的大表,行:proprietary > open-source > baseline,列分细 task — 跟 MMSI-Bench 一致,reviewer 期待这个 layout。
- **D&B "punch-line finding" 套路:**
  他们的炸点 = "不仅同 model 重复,**不同 model 也重复**" — 后者是真正反直觉的 punch line,因为反 ensemble 直觉。BenchCAD 等价 punch line 候选:
  (a) **"Visual fidelity ≠ parametric correctness"** — model 能画出像样图,但 STEP 参数全错,GT 替换 1 个数都不对;
  (b) **"Simple-family ceiling"** — 即使最简单 family,SOTA 也只到 X%,且 scaling model size 不带来收益(这跟 MMSI-Bench 的 InternVL3-1B vs 78B 只差 1.5% 一模一样的 punch);
  (c) **"Cross-model homogeneity in CAD code"** — 不同 model 生成的 CadQuery code 高度雷同,说明它们都在 mimic 同一份 training corpus 而不是真理解 geometry。挑一个最炸的当 paper 的 sticky term。
- **structural 标杆:**
  D&B reviewer 的 hard requirement(从这篇能反推): (i) **真实数据来源**(他们 mine WildChat,而非合成 — 我们的 verified_parts 来自 Fusion360 + DeepCAD 真实 dataset 可对标);(ii) **显式 taxonomy** 且每类都有占比和例子;(iii) **dense human anno**(25 anno/example,远超 HelpSteer3 的 3)— 我们对应 verified_parts.csv 每个有 GT STEP + 4 view + IoU,等价"machine-verified ground truth";(iv) **多 model 大规模 evaluation** ≥ 25 model;(v) **每个 finding 都给 quantitative 数字 + qualitative 例子双佐证**;(vi) **error / failure 类型化**(参考 MMSI-Bench 的 4 类 error 分类)。

## 5. 一句话评价 (放在我们 paper 哪里 / 是否引用)
Must-cite,放 Related Work 的 "open-ended LM evaluation / D&B benchmark methodology" 段;在 Intro 里也可以引一次,作为 "近期 NeurIPS D&B 最佳论文典范,通过真实数据 + 大规模评测 + 命名 finding 揭示 model 同质化" — 帮我们 frame BenchCAD 同样要走"真实参数化 CAD 数据 + 系统评测 + 命名 finding"的路线。
