# CAD-Coder: Text-to-CAD Generation with Chain-of-Thought and Geometric Reward (NeurIPS 2025 main)

**arXiv:** 2505.19713 · **Authors:** Guan, Wang et al. (BUAA + HKU) · **Code:** 未明示 (preprint under review 时无 repo)
**One-line:** 把 text→CAD 重新表述为 text→CadQuery 代码,Qwen2.5-7B SFT + GRPO,reward = Chamfer Distance(几何) + format(syntactic),配 1.5K CoT cold-start。

## 1. Storyline (作者讲的故事)
作者认为现有 text→CAD (DeepCAD/Text2CAD 这类 command-sequence 路线) 三大缺点:(1) 不可执行验证 (2) op 词汇少 (只 sketch+extrude) (3) 难解释/编辑。他们改用 CadQuery (Python parametric DSL) 作 proxy 表征,可直接执行验证 + 词汇丰富 + LLM 天然擅长 Python。但 SFT alone 不够 (多个等价 script 同一几何),于是加 GRPO RL,reward 用 CD 直接打几何相似度,加 CoT cold-start 让模型先 plan 再写代码。

## 2. Claim 链条 (各段论证)
- §1 Intro: 三个 contribution: (a) 重新 formulate 为 text→CadQuery (b) two-stage SFT+GRPO + CoT + CAD-Specific reward (c) 110K 数据集 + 1.5K CoT。
- §2 Related: code-gen LLM (CodeLlama, GPT-4) + GRPO + CoT;CAD gen 分 B-rep (HoLa) vs command-seq (DeepCAD/Text2CAD/CAD-MLLM/CADFusion) vs CadQuery (CAD-Recode 从点云、Query2CAD/CAD-Assistant 直接 prompt);自己定位 text→CadQuery 的 trained model 路线。
- §3 Method/Dataset: Qwen2.5-7B-Instruct + SFT (8K 高质量) + GRPO (CD reward 分段函数:CD<1e-5→1.0,CD>0.5 或执行失败→0,中间线性);CoT 6 步骤模板;1.5K CoT cold-start 2 epoch。
- §4 Experiments: Mean/Median CD + IR;baseline = Text2CAD + 5 个 zero-shot LLM (Claude-3.7-sonnet/GPT-4o/Deepseek-V3/Qwen2.5-72B/Qwen2.5-7B);ablation 拆 SFT/CoT/GRPO 三件;数据质量 8K vs 70K 比较。
- §5 Conclusion/Limitations: 复杂多组件结构 sub-component 对齐有问题;细节几何 (薄壁、紧公差) 触发 reward hacking;承认 RL 不擅长 overlapping features。

## 3. 关键佐证 (具体数字 / 表格)
- 数据规模: 110K text-CadQuery-3D triplets (基于 Text2CAD 178K NL desc 反向用 Deepseek-V3 合成 + CD 筛);分级:8K (CD<1e-4) / 70K (CD<1e-3) / 32K hard (CD>1e-3);1.5K CoT 样本人工 refine。
- 训练: 8×NVIDIA A800 80GB;SFT 7h、GRPO 146h (~6 天);batch size 64 (SFT) / 384 (GRPO);lr 1e-5;k=8 candidates/prompt;β=0.001 KL。
- 主表 (Text2CAD test set,CD ×10³): CAD-Coder Mean CD **6.54** / Median **0.17** / IR **1.45%**;Text2CAD baseline 29.29 / 0.37 / 3.75 (Mean CD 4.5× 优势);GPT-4o 133.52/45.91/93;Claude-3.7-sonnet 186.53/134.16/47.03;Qwen2.5-7B (zero-shot) 202.35/169.86/98.83。
- Ablation: SFT-only Mean CD 74.55;w/o SFT 76.20;w/o CoT 17.34;Full 6.54 → 各组件都重要。
- 数据质量消融: 70K 中等 → 9.89;8K 高质量 → 6.54 → "quality > quantity"。
- 唯一 trained baseline 是 Text2CAD;其余 5 个 LLM 都是 zero-shot prompt (没 fine-tune)。
- 失败模式 (Sec F):多组件 spatial alignment 错位 + 薄壁/重叠 reward hacking。
- 编辑能力 (Sec E):"未训练 edit data 但能简单 edit",给了 prompt 模板但无定量评测。

## 4. 对 BenchCAD 的启发 (improvement / 偷什么 / 超什么)
- **可以偷的写法:** "reformulate text-to-CAD as text-to-CadQuery" 这种"换表征即 contribution"的 framing;DeepCAD vs CadQuery 对比图 (Fig 1) 三栏 (text / DeepCAD tokens / CadQuery code) 同一物体三种表征,极有说服力,我们写 related 时可同图模板比 token-seq vs code;reward design 分段函数细节 (CD<1e-5→1, >0.5→0, 中间线性) 可以借;ablation 表把 "w/o X" 行排干净极清晰;quality > quantity 这个故事钩子很好用。
- **我们超过他们的点:**
  - **数据 provenance**:他们 110K 全是 Deepseek-V3 反向合成 CadQuery,GT 几何来自 Text2CAD (即 DeepCAD 数据底)。即数据底仍是 DeepCAD 的 sketch+extrude bias;BenchCAD 106 family 程序化合成,GT 几何/code/views 全部来自我们 builder,无 LLM hallucination。
  - **op 多样性**:他们虽用 CadQuery,但实际 GT 来自 sketch+extrude command sequence 翻译,op 覆盖窄;我们 106 family 直接覆盖 fillet/loft/revolve/boolean。
  - **评测多样性**:他们 1 task (text→CAD),1 metric 系列 (CD + IR);我们 5 task (img2cq/qa_img/qa_code/edit_img/edit_code) + IoU + edit pass-rate。
  - **rotation/scale invariance**:他们 CD 依赖 normalize 到 unit bbox,坐标系变化敏感;我们 rotation-invariant IoU + scale-invariant prompt。
  - **edit 评测**:他们 §E 承认 edit 是 "promising" 但无数字;我们 edit_img/edit_code 是 first-class task。
- **必须正面回应的点:** 
  1. 他们已经在 NeurIPS 2025 main 把 "text→CadQuery + RL" 立住了,我们必须明确 task 不是 text→CAD 而是 multi-modal benchmark (尤其 img2cq);
  2. CD reward 的设计很 elegant 我们 related 必须承认;
  3. 110K 规模 vs 我们 20K verified + 162K GenCAD 在量级上略输,要从 "verified by execution + multi-task" 维度反击;
  4. quality > quantity 论点反过来支持我们 small-but-curated 的合理性。
- **可以借鉴的 metric / 评测协议:** 1) Mean/Median CD + IR (×10³ 量级习惯);2) Reward 分段函数模板 (我们 edit pass-rate 也可以借鉴 piecewise reward);3) zero-shot LLM baseline 阵容 (Claude/GPT-4o/Deepseek-V3/Qwen 系) 是 NeurIPS 2025 标准 baseline,我们必须包含;4) ablation 拆 strategy 的 "w/o X" 表布局。

## 5. 一句话定位 (related work 行文用)
CAD-Coder [Guan et al., NeurIPS 2025] 把 text→CAD 重新表述为 text→CadQuery 并用 GRPO + 几何 (CD) reward 训练 Qwen2.5-7B,在 Text2CAD test 上 Mean CD 6.54 (4.5× 优于 Text2CAD);但其训练数据仍由 LLM 反向合成自 Text2CAD/DeepCAD 底库 (sketch+extrude bias),且只评单一 text→CAD 任务,与我们程序化合成的 106-family 数据 + 5-task multi-modal benchmark (含图像和编辑) 互补。
