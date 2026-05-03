# Text2CAD: Generating Sequential CAD Models from Beginner-to-Expert Level Text Prompts (NeurIPS 2024 D&B)

**arXiv:** 2409.17106 · **Authors:** Khan, Sinha et al. (DFKI/RPTU/MindGarage/BITS) · **Code:** sadilkhan.github.io/text2cad-project/
**One-line:** 第一个 text→parametric CAD 框架,在 DeepCAD 基础上 LLM+VLM 合成 4 级文本 prompt,训练 BERT+autoregressive Transformer 直接出 sketch-extrude tokens。

## 1. Storyline (作者讲的故事)
作者认为 modern CAD 缺 AI 辅助,text→3D 现有方法都只能出 mesh/NeRF 不可编辑;text→parametric CAD 没人做过。两大 blocker:(1) 没数据集 (无 text↔CAD 序列配对) (2) 没合适架构。他们造数据 (LLaVA-NeXT 出 shape 描述 + Mixtral-50B 出 4 级 instruction) + 训练 BERT-encoder/auto-regressive decoder 的 Text2CAD Transformer。关键洞察:用 multi-level prompt (L0 abstract → L3 expert) 让模型同时服务新手和专家。

## 2. Claim 链条 (各段论证)
- §1 Intro: 我们是 first text→parametric CAD;LLM 直接生成 FreeCAD 脚本不 designer-friendly,VLM (LLaVA) 把 hollow cylinder 看成 toilet paper 不行 → 必须造专属数据 + 专属网络。
- §2 Related: 数据上对比 ABC/Fusion360/DeepCAD,指出"无 text 标注";方法上对比 SketchGen/Polygen/HNC/CAD-SIGNet,定位自己是"first auto-regressive 直接 text→CAD"。
- §3 Method/Dataset: 两阶段 annotation pipeline (VLM shape desc → LLM multi-level NLI),DeepCAD 150k 训练 + 8k 测试 × 4 级 prompt = ~600k 训练样本;Transformer 8 层 decoder + BERT encoder + Adaptive Layer。
- §4 Experiments: F1 (line/arc/circle/extrusion) + median/mean Chamfer Distance + Invalidity Ratio;baseline 是 DeepCAD 改造版;另跑 GPT-4V 二选一评估 + 5-人 user study。
- §5 Conclusion/Limitations: LLaVA 对透视敏感、没 standardized benchmark、DeepCAD 数据 imbalance (rect+cyl 太多)。

## 3. 关键佐证 (具体数字 / 表格)
- 数据规模: ~170K CAD 模型, ~660K 文本标注 (4 级 × 170k);训练集 ~600k samples,测试 ~32k。
- 标注成本: 10 天跑完;用 LLaVA-NeXT + Mixtral-50B (MoE) + Mistral-7B。
- CAD 表示: 8-bit 量化 sketch+extrusion tokens, 256 类标签,序列长度 Nc=272,文本最大 Np=512。
- 训练: 1×A100-80GB,160 epochs,2 天,lr=1e-3 AdamW,L=8 decoder blocks/8 heads,d=256。
- 主表 (L3 expert prompts): Text2CAD vs DeepCAD: F1 line 81.13 vs 76.78、F1 arc 36.03 vs 20.04 (+80%)、F1 circle 74.25 vs 65.14、F1 extrusion 93.31 vs 88.72;Median CD 0.37 vs 32.82 (×88.7);Mean CD 26.41 vs 97.93;IR 0.93% vs 10.00% (×10.75)。
- GPT-4V eval (1000 samples/level): Text2CAD 在 L0/L1 略输或持平 (51.8/48.35),L2/L3 大胜 (58.8/63.24 vs 40.2/36.06)。
- User study: 5 designer × 100 sample/level,趋势同 GPT-4V。
- 唯一 baseline 就是 DeepCAD 改造 + 自己 ablation (w/o Adaptive Layer)。
- Adaptive Layer 让 IR 降 ~2.9x、arc F1 +32.56%。

## 4. 对 BenchCAD 的启发 (improvement / 偷什么 / 超什么)
- **可以偷的写法:** "first AI framework for X" 一句话 hook;两阶段 annotation pipeline 图 (VLM shape + LLM detail) 模板可借;multi-level prompt (L0/L1/L2/L3) 的概念既给评测维度也支撑写作;GPT-4V 二选一评测 + user study 的双保险评测格式给我们启发可以做。
- **我们超过他们的点:**
  - **数据多样性**:他们 170K 来自 DeepCAD (sketch+extrude only),自己承认 imbalance 偏 rect/cyl;BenchCAD 106 family 可控合成,严格 family 平衡。
  - **几何 op 覆盖**:他们只支持 sketch+extrude,我们覆盖 fillet/loft/sweep/revolve/boolean 等 (CadQuery API)。
  - **任务多样性**:他们只评 text→CAD;我们 5 task (img2cq/qa_img/qa_code/edit_img/edit_code)。
  - **评测协议**:他们 CD 是 unit-bbox 归一化后的,我们 rotation-invariant IoU + scale-invariant prompts 更严谨。
  - **Code 表征**:他们用 8-bit 量化 token (256 类),不可执行;我们直接 CadQuery Python 可执行 + 可编辑。
  - **Verifiability**:他们 IR 通过 token validity 间接判,我们 build pipeline 直接 IoU 验证。
- **必须正面回应的点:** (1) 4-level prompt 难度梯度的 framing 很强,我们 difficulty 分级 (easy/medium/hard) 必须明确 grounding 何在 (param range? op count?);(2) 660K text 标注规模庞大,我们 162k GenCAD pairs + 20k verified parts 数量上比文本标注少,要从 verifiability/diversity 角度反击;(3) 他们已经在 NeurIPS D&B 立住了 text→CAD 数据集 brand,我们要明确 "20k 合成 + 程序化生成 ≠ LLM-paraphrased 标注"。
- **可以借鉴的 metric / 评测协议:** F1 (primitive type) + median/mean CD + IR 三件套;GPT-4V 多视图二选一 verdict 协议 (with "Undecided" option);1000 sample/level 的固定 eval 数量。

## 5. 一句话定位 (related work 行文用)
Text2CAD [Khan et al., NeurIPS 2024 D&B] 第一次为 DeepCAD 数据加 4 级 (abstract→expert) 自然语言标注并训练 BERT+autoregressive transformer 出 sketch-extrude token 序列;但其底层数据继承 DeepCAD 的 rect/cyl 偏置 + sketch+extrude 单一 op + token 序列不可执行,与我们 106-family 程序化合成、CadQuery 可执行代码、5-task benchmark 的定位正交。
