# Generating CAD Code with Vision-Language Models for 3D Designs (CADCodeVerify) (ICLR 2025)

**arXiv:** 2410.05340v2 · **Authors:** Alrashedy, Tambwekar et al. (Georgia Tech) · **Code:** github.com/Kamel773/CAD_Code_Generation
**One-line:** VLM 自问自答验证生成的 CadQuery 代码,迭代 refine;同时提出 CADPrompt — 200 个 NL→CadQuery 专家代码 benchmark,首个 CAD code-gen quantitative benchmark。

## 1. Storyline (作者讲的故事)
VLM 能从自然语言生 CadQuery 代码,但常和用户意图偏离。现有 refinement 要么靠人 (Makatura/Nelson),要么只丢图给 VLM (3D-Premise),效果有限。提出 CADCodeVerify:VLM 先自动从 prompt 生成 2-5 个 yes/no 验证问题,再看 4 个角度的 render 图自答,把 No 的问题汇成 ameliorative feedback 喂回 VLM 改代码。同时人工标注 CADPrompt:200 个 3D 物体 + NL prompt + 专家 CadQuery 代码,按 mesh/geom 复杂度和 compile 难度分层。GPT-4 + CADCodeVerify 把 PCD 距离降 7.30%,compile rate 提 5.5%。

## 2. Claim 链条 (各段论证)
- §1 Intro: 现有 LLM-CAD 方法靠 human-in-the-loop refinement,贵且慢。本文 = 自动 refine + 首个 quantitative benchmark。
- §2 Related: LLM code-gen feedback 已有 self-explain (Chen)、static-analysis (Alrashedy)、interpreter (Madaan)、self-correct (Welleck);3D 多模态学 shared-embedding (PointBind/CLIP) 但不能生成;3D 生成传统是 GAN/VAE/Diffusion → 输出 point cloud/voxel 不可制造;CAD code-gen 之前只有 Makatura/Nelson 的 case study + 3D-Premise 单图 refine。
- §3 Method/Dataset: 三步 pipeline — (1) generate y0 from x; (2) execute via CadQuery,失败用 compiler error 反馈 repair (最多 N 次); (3) CADCodeVerify refine M 次:VLM 生 Q={q1..qn} → 看 0/90/180/270 度 4 张 render + Q + x → CoT 答 A (允许 "Unclear") → 汇 feedback Fref → 改代码,只针对 No 的问题。
- §4 Experiments: 200 个 obj 选自 Wu 2021 modular CAD;NL prompt 4-pass 标注 + 验证;专家 CadQuery 代码用 Blender 验证。分层:mesh complexity (按面+顶点中位数) / compilation difficulty (3 LLM × 2 prompting 共 6 次,≥4 通过为 Easy) / geometric complexity (4 级专家评)。
- §5 Conclusion/Limitations: PCD/Hausdorff 是粗 metric,捕捉不到结构性 logic 差异(如桌腿和桌面之间的小缝);prompt 写法敏感,同物体多种合法描述。

## 3. 关键佐证 (具体数字 / 表格)
- Table 1 CADPrompt: 200 obj,Simple 17 / Moderate 39 / Complex 87 / Very Complex 57;mesh 顶点 6-540 (avg 88.8),面 8-1092;NL 9-188 词 (avg 50);Python 6-46 行 (avg 16.6) / 18-117 token。
- Table 2 GPT-4 few-shot: Generated PCD 0.155 → CADCodeVerify 0.127,IoGT 0.939 → 0.944,compile 96.0% → **96.5%**;3D-Premise compile 反降到 91.0%。
- Table 2 Geometric Solver* (上界,需 GT): PCD 0.103,但需访问 GT,不实用。
- Table 2 Gemini Few-shot: 3D-Premise 让 compile 从 85% 掉到 81.5%;CADCodeVerify 维持 85%。
- Table 2 CodeLlama Few-shot (无多模态,用 GPT-4 当 verifier): compile 67% → 73.5%。
- Fig 4 Hard 子集: CADCodeVerify Refine-1 把 compile 提约 9%;3D-Premise 反降 20% (→62%)。
- Table 3 ablation (100 子集): zero-shot QA gen PCD 0.141 vs few-shot 0.126;无 Iref 图 0.153 vs 有 0.126 — 图很关键。
- Table 4 50 样本 Human-in-the-Loop: CADCodeVerify PCD 0.137 / IoGT 0.948;HITL 0.120 / 0.944 — HITL 略好但接近。
- QA 答案准确度: 人工核查 50 个,Refine-1 64.6%,Refine-2 68.2% — 验证答案本身就有错。
- ICP 对齐 + 单位 cube 归一化;失败惩罚 PCD = √3 / IoGT = 0。
- 三模型 compile rate 基线: GPT-4 96.5%,Gemini 85%,CodeLlama 73.5%。

## 4. 对 BenchCAD 的启发
- **可以偷的写法:** "现有 CAD code refinement 要么 HITL 要么单图 reflection — 都效果差/不可扩展" 是干净的 motivation;CADPrompt 三轴分层 (mesh / compile / geom complexity) 写法很清楚,可借鉴 BenchCAD difficulty stratification 报告。Table 2 在三模型 × 两 prompting × 多反馈机制对比是好模板。Limitations 段直接点出 "PCD/Hausdorff 抓不到结构 logic 差异",我们就借此正向引出 family-aware / rotation-invariant IoU 的必要性。
- **我们超过他们的点:** (1) 规模:CADPrompt 200 obj vs BenchCAD 20143 verified + 162k GenCAD pairs (差两个数量级)。(2) 任务覆盖:他们只做 NL→code 单任务,BenchCAD 是 5-task (img2cq, qa_img, qa_code, edit_img, edit_code)。(3) verification 协议:他们提专家代码且 IoGT/PCD 用 ICP+ unit cube,但 PCD 自己承认捕不到结构;BenchCAD rotation-invariant IoU 直接命中此痛点。(4) prompt scale invariance:他们 prompt 含具体比例 ("about 2/3rd"),仍是绝对几何;BenchCAD scale-invariant prompt 设计是新点。(5) family 注册:他们样本来自 Wu 2021 一堆 mesh,无 family 结构;BenchCAD 106 families 是参数化生成。
- **必须正面回应的点:** (a) CADPrompt 是 ICLR 2025 公开 benchmark,BenchCAD 必须正面比较:为什么不直接拿 CADPrompt 评?答:200 太小、无 family 标签、prompt 含绝对几何。(b) 他们 IoGT 是 bbox 重叠,我们要解释 rotation-invariant IoU 是 mesh-level 且对 SE(3) 稳健。(c) 他们已用 4-view render + VLM yes/no QA — 我们的 qa_img 任务必须明确区别(我们的 QA 是 ground-truth 题库 vs 他们的自生成验证题)。(d) 他们的 refinement loop 思路也可作为 BenchCAD 上 baseline。
- **可以借鉴的 metric / 评测协议:** ICP 对齐 + unit-cube 归一化(我们已有 SE(3) 不变 IoU,可对齐协议方便比较);compile rate / IoGT / PCD / Hausdorff 一并报;失败惩罚用最大可能距离 (√3) 是公允做法;ablation 用固定 100 子集 GPT-4 few-shot;HITL upper bound 是 honest 写法,我们 5-task 也可有 expert upper bound。

## 5. 一句话定位 (related work 行文用)
CADCodeVerify [Alrashedy & Tambwekar et al., ICLR'25] 提出首个 CAD code-generation 定量 benchmark CADPrompt (200 NL prompts + 专家 CadQuery 代码) 并以 VLM 自问自答 yes/no 视觉验证作 refinement,提升 GPT-4 PCD 7.3% / compile 5.5% — 但规模仅 200 例、无 family 结构、IoGT 基于 bbox 且 prompt 含绝对几何;BenchCAD 在 verified 规模 (×100)、family 化参数生成 (106 families)、rotation-invariant IoU、以及 5-task 多模态评测协议方面进一步推进 CAD code 评测基础设施。
