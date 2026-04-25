# cadrille (ICLR 2026)

**arXiv:** 2505.22914v3 (17 Feb 2026) · **Authors:** Maksim Kolodiazhnyi¹², Denis Tarasov²³, Dmitrii Zhemchuzhnikov¹², Alexander Nikulin¹², Ilya Zisman²⁴, Anna Vorontsova, Anton Konushin¹², Vladislav Kurenkov²⁴, Danila Rukhovich⁵† (corresp.: rukhovich@mechins.sci.am)
**Affiliations:** ¹Lomonosov MSU · ²AXXX (匿名, Moscow Russia) · ³ETH Zurich · ⁴Innopolis Univ · ⁵Institute of Mechanics, Armenia
**Code/HF:** github.com/col14m/cadrille · maksimko123/cadrille (SFT) · maksimko123/cadrille-rl (RL)

## 1. Lab connection check
- **同一作者群高度重叠**: Rukhovich (CAD-Recode 一作, ICCV'25) 在 cadrille 任 corresp.; Zhemchuzhnikov (CADEvolve 关联用户名 zhemdi) 同列作者. Elistratov (CADEvolve 一作, kulibinai) 未在 cadrille 作者表 — 但同 lab 圈 (Innopolis/MSU/AIRI 系俄系 ML).
- **结论**: cadrille (CAD-Recode 续作) → CADEvolve (cadrille 续作) 实为同一俄系 lab 三连发. CADEvolve 把 cadrille 当 RL baseline 合理.
- 资金来源: Russian Ministry of Economic Dev (subsidy 000000C313925P4H0002).

## 2. Method one-shot
- **Backbone**: Qwen2-VL-2B (论文确认 "we also use a Qwen LLM model as in CAD-Recode (Qwen2-VL-2B against Qwen2-1.5B)")
- **Inputs**: point cloud + multi-view images + text — **三模态统一在同一 VLM**. 点云走 single linear projection (沿 CAD-Recode), FPS 采样, 不用法向; image 走原 VLM visual encoder; text 走 tokenizer.
- **SFT data**: CAD-Recode 1M procedural CadQuery + DeepCAD 160k (多模态版本来自 Text2CAD).
- **RL**: 三阶段 — (1) VLM 预训练 (复用) → (2) SFT (procedural) → (3) RL (handcrafted, **无需 CAD seq 标注, 只要 mesh**). Reward `R = r_IoU + r_invalid`, IoU×10, invalid=-10. Hard-example mining: 仅用 SFT 平均 reward < 7.5 的样本.
- **算法**: 三种都试 — DPO (offline) / GRPO 变体 / **Dr. CPPO** (= Dr. GRPO 去 ref model + CPPO 取强信号 sample, 论文最终采用).

## 3. Headline scores (median CD ×10³ / Mean IoU% / IR%)
| Bench | cadrille SFT | cadrille RL (Dr.CPPO) | Prior SOTA |
|---|---|---|---|
| **DeepCAD pt** | 0.18 / 87.1 / 2.1 | **0.17 / 90.2 / 0.0** | CAD-Recode 0.18/87.1/3.1 · CAD-SIGNet 0.29/77.3/5.0 |
| **DeepCAD img** | 0.18 / 86.1 / 1.5 | **0.17 / 92.2 / 0.0** | CADCrafter 0.26/-/3.6 · LRM→CAD-Recode 0.53/69.8/14.3 |
| **DeepCAD txt** | 0.21 / 81.1 / 1.4 | — | Text2CAD 0.37/71.5/3.7 · Text-to-CadQuery 0.22/-/1.3 |
| **Fusion360 pt** | 0.19 / 79.8 / 2.8 | **0.19 / 85.0 / 0.2** | CAD-Recode 0.19/79.1/5.0 |
| **Fusion360 img** | 0.20 / 77.6 / 3.2 | **0.17 / 84.6 / 0.0** | LRM→CAD-Recode 0.62/62.5/18.7 |
| **CC3D pt (real)** | 0.54 / 61.3 / 5.9 | **0.47 / 67.9 / 0.2** | CAD-Recode 0.54/60.5/9.8 |
| **CC3D img** | 3.2 / 56.1 / 7.7 | **0.57 / 65.0 / 0.1** | LRM→CAD-Recode 1.19/50.1/20.1 |

RL 把 IR 几乎 0. 关键 finding: 在 image 上 RL 同时拉高 point cloud (跨模态迁移).

## 4. Training compute / data
- 论文未给 GPU/小时具体数 (附录可能有). T=1.0 sampling, K=5 (DPO), G samples (Dr.CPPO).
- Data: SFT = R_pi (CAD-Recode 1M) + D_pit (DeepCAD 160k 三模态); RL = D_i⁻ + F_i⁻ (DeepCAD + Fusion360 mesh, 无 seq).
- 关键 trick: SFT mix R+D 反而掉点 (Tab.3 row4 vs row3) — RL 才能弥合 domain gap.

## 5. Released artifacts
- HF SFT: maksimko123/cadrille (Qwen2-VL-2B SFT) — 公开
- HF RL: maksimko123/cadrille-rl — 公开
- Code: col14m/cadrille — 推理 + 训练
- License: 未在论文声明 (查 repo)
- Inference: takes mesh/pcd/images/text → CadQuery .py, no LLM API call (本地 Qwen2-VL-2B 推理).

## 6. CADEvolve vs cadrille direct compare
| 维度 | cadrille | CADEvolve |
|---|---|---|
| Backbone | Qwen2-VL-2B | Qwen2-VL-2B |
| Modality | point/image/text 统一 | image (8-view grid) only |
| Data scale | 1M (R) + 160k (D) | 2.7M scripts |
| Data source | CAD-Recode procedural + DeepCAD | 46 primitives + GPT-5-mini evolution |
| RL | DPO / Dr.CPPO (Dr.GRPO+CPPO) online | Dr.GRPO + CPPO |
| Reward | 10·IoU + (-10 if invalid) | 10·IoU |
| DeepCAD med CD/IoU (pt) | 0.17 / 90.2 | — (img only) |
| DeepCAD med CD/IoU (img) | 0.17 / 92.2 | 0.15 / 92.6 |
| Fusion360 med CD/IoU (img) | 0.17 / 84.6 | 0.16 / 87.2 |
| MCB | 未测 | 0.52 / 55.2 |
| CC3D real (img) | 0.57 / 65.0 | 未测 |

CADEvolve = cadrille pipeline + 更大更多样的合成数据 (evolutionary).

## 7. 对 BenchCAD 意义
- 两个 HF 模型均 inference-only, 本地可跑 → 适合 BenchCAD transfer Table.
- **建议测 cadrille-rl + CADEvolve 双 baseline** — 一个证明 RL 普适性, 一个是当前最强.
- Op coverage: cadrille SFT 数据来自 CAD-Recode (sketch+extrude only, 缺 cut/symmetric), 但 RL 阶段用 DeepCAD mesh 弥补 → 仍偏 sketch-extrude. BenchCAD 若含 fillet/chamfer/loft 类 op, cadrille 可能崩.
- 评测可借 cadrille 的 metric 协议: median CD×10³ on 8192 pts in [-0.5,0.5]³ + mean IoU% + IR%.
- CC3D real-world 是 cadrille 主打 robustness 卖点, BenchCAD 若想差异化应避免直接重叠.

## 8. 一句话 related-work positioning
近期多模态 CAD 重建主流路径 (cadrille [Kolodiazhnyi et al., ICLR'26], CADEvolve [Elistratov et al., 2026]) 共同采用 "VLM (Qwen2-VL-2B) + 程序化合成 SFT + 在线 RL (Dr.GRPO/Dr.CPPO, IoU reward)" 范式, 在 DeepCAD/Fusion360/CC3D 上把重建 IoU 推到 ~90% 同时把 invalid rate 压到 <0.5%, 但仍局限 sketch-extrude op 与单模态合成数据分布, BenchCAD 通过 106 family 程序化覆盖+多 op 类型补齐这一空白.
