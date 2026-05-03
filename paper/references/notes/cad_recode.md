# CAD-Recode: Reverse Engineering CAD Code from Point Clouds (ICCV 2025)

**arXiv:** 2412.14042v2 · **Authors:** Rukhovich et al. (SnT, Univ. Luxembourg + Artec3D) · **Code:** 提到将开源 1M 数据集
**One-line:** 用 Qwen2-1.5B + 轻量 point cloud projector 把点云 fine-tune 成可执行 CadQuery Python 代码,程序合成 1M 训练集,DeepCAD/Fusion360/CC3D 全面 SOTA。

## 1. Storyline (作者讲的故事)
现有 CAD 反向工程 (DeepCAD/CAD-SIGNet 等) 用自定义 token 序列表示 sketch-extrude,既难解释又要从头训网络学语法+几何。LLM 已经会写 Python,CadQuery 又是 Python CAD DSL,两者结合天然合拍。于是把任务重写成 "点云 → CadQuery Python",用 pre-trained Qwen2-1.5B 当 decoder + 256 点 projector,再程序合成 1M sketch-extrude 序列做训练集。三个数据集(DeepCAD/Fusion360/CC3D)全 SOTA,而且代码可读 → 接 GPT-4o 直接做 CAD-QA 和 sliders 编辑。

## 2. Claim 链条 (各段论证)
- §1 Intro: 现有方法 = 自定义表示 + 手工数据 + 从头训网络 → 不可解释、不能直接编辑、规模受限。提出三贡献:CadQuery 代码表示 / LLM-based 模型 / 1M procedural 数据集。
- §2 Related: LLM+点云任务都是双阶段对齐 (PointLLM 等);CAD 反向工程要么自定义 token 要么 CSG/B-Rep,均远离现代 CAD workflow;Img2CAD 用 GPT-4V 但仍要单独 transformer 推参数。
- §3 Method/Dataset: CadQuery 代码相比 DeepCAD token 序列(`SOL Line ... Ext. ...`)有模块化(可复用坐标/平面、可调用 box/cylinder 高层 API)+ 可解释 + LLM 兼容三大优势。1M 数据集流程:Algo 1 generate2DSketch (3-8 个 circle/rect 组合 + bool) → Algo 2 extrude + union + normalize-quantize-simplify-validate-dedupe。坐标量化到 [-100, 100] 整数。
- §4 Experiments: 模型 = FPS 256 → Fourier PE → linear → Qwen2-1.5B,query token dim 1536。NLL loss,AdamW 0.0002,100k iters,单卡 H100 12h。test-time 采样 10 个候选选 min CD。
- §5 Conclusion/Limitations: 仅 sketch+extrude,不能 revolution/fillet/chamfer;CC3D 复杂件还差;未来扩 LLM/数据/操作集。

## 3. 关键佐证 (具体数字 / 表格)
- Table 1 DeepCAD 测试集: prev best CAD-SIGNet mean CD 3.43, IoU 77.6, IR 0.9 → CAD-Recode (1M) mean CD **0.30**, IoU **92.0**, IR 0.4。10× CD 改善,IoU 提 14 点。
- Table 1 Fusion360: CAD-SIGNet mean CD 7.37 / IoU 65.6 → CAD-Recode 0.35 / **87.8**。
- Table 2 CC3D 真实扫描: CAD-SIGNet med CD 2.90 IoU 42.6 → CAD-Recode 0.31 IoU **74.2**(IR 0.3)。
- Table 3 ablation: 同样 160k,DeepCAD 数据训 IoU 80.7,procedural 160k 训 IoU **88.3** → procedural 数据本身比真实数据更好学。
- Table 4 architecture: 256 pts + Qwen1.5B 最佳 (DeepCAD IoU 92.0);0.5B 也只差 1-2 点。
- Table 5 SGP-Bench CAD-QA: PointLLM 42.3% / CAD-SIGNet→GPT-4o 63.2% / CAD-Recode→GPT-4o **76.5%**。
- 训练集 = 1M procedural CadQuery scripts,通过 PythonOCC + BRepCheck 校验 + dedupe (借自 [51])。
- inference: 10 candidates × 不同 FPS 采样,选 min CD → 主要降 IR(无采样 IR 4.9% vs 有 0.4%)。
- compact training code: 三段式 (import / sketch planes / sketch-extrude+union)。
- Qwen2-1.5B 选型理由:HumanEval Python code 能力 + 模型小训练快。

## 4. 对 BenchCAD 的启发
- **可以偷的写法:** "现有数据集 hand-crafted、parsed-from-proprietary、规模有限、design feature 不可控"是直接可复用的 motivation 锤;Algo 1/2 procedural pipeline 写法清晰,我们也可以列 family 注册表式 algo。Table 1/2/3 三层 (SOTA 比较 / 真实 OOD / ablation 数据来源) 表格结构干净,可借鉴。
- **我们超过他们的点:** (1) 他们仅 sketch+extrude,自己也承认 CC3D 复杂件失败;BenchCAD 106 families 覆盖 revolve/sweep/loft/fillet/chamfer/pattern。(2) 他们的"数据集"本质是训练 corpus,无 benchmark 协议、无任务划分;BenchCAD 是 5-task benchmark + verified 数据集。(3) 他们 1M 是 unverified raw exec-pass,BenchCAD 20143 是 IoU≥0.99 verified。(4) 他们仅做 point→code 单任务,我们做 img2cq + qa + edit 五任务,且 rotation-invariant IoU。
- **必须正面回应的点:** (a) 他们已证明 1M procedural 训练 > 真实 DeepCAD,审稿人会问"你 20k 凭什么够",答:我们是 verified evaluation set 而非训练 corpus,目标是衡量模型而非训模型;且我们提供 162k GenCAD 训练对。(b) CadQuery 代码表示已被他们定为 baseline,BenchCAD 必须明确说我们沿用 CadQuery 但加 family-level structured params。(c) CAD-Recode 已经把 GPT-4o + CAD code 用于 QA 和编辑,BenchCAD 的 qa/edit task 必须区别于 SGP-Bench 那种基于 sequence 的 QA(我们用图)。
- **可以借鉴的 metric / 评测协议:** mean+median CD、IoU(mesh 体素)、IR (Invalidity Ratio = exec fail rate);test-time best-of-N + min-CD selection;按数据来源分表 (synth / Fusion360 / real-world);ablation 写法 (训练量 / test-time sampling / 架构维度) 三表分离。

## 5. 一句话定位 (related work 行文用)
CAD-Recode [Rukhovich et al., ICCV'25] 首次将 pre-trained LLM (Qwen2-1.5B) 用于 point-cloud → CadQuery Python 反向工程,以 1M procedural 训练集刷新 DeepCAD/Fusion360/CC3D SOTA,但仅覆盖 sketch-extrude 操作、训练 corpus 无 verification 协议、亦无 image-conditioned 或 edit/QA 任务的 held-out benchmark — BenchCAD 在覆盖广度 (106 families × 多操作)、verified IoU≥0.99 评测集、以及 5-task 多模态评测协议三方面互补。
