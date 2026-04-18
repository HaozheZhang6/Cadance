好，文章就按这 **4 张图** 来重构。这样整篇会更像一篇 **CVPR workshop paper**，因为每一节都围绕一个清晰的视觉论点展开，而不是平铺工程细节。

我先给你一个新的**整篇叙事骨架**，然后直接给你一版可用的英文初稿框架。

---

# 一、文章总逻辑改成 4 图驱动

## Figure 1 对应：问题定义 + 核心 insight

这一段回答：

**为什么这个问题难？为什么你这个方法值得做？**

主线是：

* 复杂 CAD 生成是开放式、长链条、易碎的
* 直接生成最终几何很难验证
* 我们把它改写成 **verifiable program synthesis**
* 一旦是 executable code，就能做强验证
* 强验证让 noisy generation 变成 high-precision data

所以 **Intro 前半段** 应该围绕 Figure 1 来写。

---

## Figure 2 对应：方法主流程

这一段回答：

**系统怎么工作？**

主线是：

* 输入是什么
* 生成 CAD program
* 执行成 geometry
* 做几何/视觉/元数据验证
* 通过的进入 verified store
* 失败的进入 repair / manual check
* 最后组装成 training-ready data

所以 **Method 的主干** 应该围绕 Figure 2 来写。

---

## Figure 3 对应：为什么是 skill-based，不是 rigid workflow

这一段回答：

**为什么你的系统设计不是普通 pipeline？**

主线是：

* 复杂长尾失败模式是异质的
* 静态 workflow 脆弱、难扩展
* modular skills 可替换、可复用、可插人工检查
* 这让系统更便宜、更 robust、更适合复杂问题

所以 **Method 后半段 / Discussion / contribution** 应该围绕 Figure 3 来写。

---

## Figure 4 对应：案例与证据

这一段回答：

**你的方法到底在真实样本上做成了什么？**

主线是：

* 给出成功 case
* 给出失败后修复 case
* 展示 verification 的作用
* 展示 repair/manual check 的作用

所以 **Experiments / qualitative results** 应该围绕 Figure 4 来写。

---

# 二、文章结构改成这样最顺

## 1. Introduction

* Figure 1
* 讲 problem + insight
* 最后抛出 Figure 2 的方法闭环

## 2. Related Work

* CAD generation
* code-oriented CAD
* validation / data curation
* modular systems / data loops

## 3. Method

### 3.1 Problem reformulation

* Figure 1 呼应

### 3.2 Verification-guided pipeline

* Figure 2

### 3.3 Skill-based modular design

* Figure 3

### 3.4 Verified store and training-ready data

* Figure 2 收尾

## 4. Experiments

### 4.1 Evaluation setup

### 4.2 Overall statistics

### 4.3 Repair and hard-tail recovery

### 4.4 Qualitative case studies

* Figure 4

## 5. Discussion

* 为什么 code representation 重要
* 为什么 verification 不是单纯评估
* 为什么 skill 比 workflow 更适合
* 限制和未来工作

## 6. Conclusion

* 再回到 Figure 1 的一句话主旨

---

# 三、核心 claim 统一成这一句

整篇文章只守住一个主 claim：

> **We convert complex CAD generation into verifiable program synthesis, and use a skill-based verification loop to transform noisy outputs into high-precision, training-ready supervision.**

这句非常重要。
后面所有段落、图、contribution 都服务它。

---

# 四、改过后的英文摘要

## Abstract

Computer-aided design (CAD) generation is a challenging long-horizon engineering task: outputs must not only resemble a target geometry, but also remain executable, editable, and structurally valid. Existing approaches often formulate CAD generation as direct shape prediction or command-sequence generation, which makes them brittle under long construction chains and difficult to curate at scale. In this paper, we propose a **skill-based, verification-guided framework for CAD data generation**. Our key idea is to convert complex CAD generation into **verifiable program synthesis**: a large language model generates CAD programs, the programs are executed into geometry, and the resulting artifacts are filtered through geometric, visual, and metadata-based verification. Rather than relying on a monolithic workflow, we decompose the process into reusable skills for generation, execution, verification, repair, and dataset assembly. This modular design improves extensibility and robustness while accommodating hard-tail cases through manual checking. The output of the system is a collection of **high-precision, training-ready verified program–geometry pairs**. We evaluate the framework without downstream retraining, focusing instead on data quality, verifier precision, hard-case recovery, and coverage on complex examples. More broadly, our results suggest that, for complex engineering tasks, a practical path to scalable data generation is not direct open-ended synthesis, but the combination of executable representations, strong verification, and modular skill composition.

---

# 五、改过后的英文 Introduction

## 1. Introduction

Computer-aided design (CAD) is a foundational representation in engineering and manufacturing because it captures not only the final geometry of an object, but also the underlying construction process through sketches, operations, and parameters. Compared with meshes or point clouds, CAD programs are editable, interoperable with downstream simulation and manufacturing tools, and closer to how real engineering artifacts are produced. This has motivated a growing line of research on parametric and sequential CAD generation, as well as more recent code-oriented approaches that treat CAD as a structured executable language.

Despite this progress, complex CAD generation remains fundamentally difficult. CAD construction is a long-horizon, constraint-heavy process in which a small local mistake can invalidate an entire design. Direct generation of final geometry is especially challenging because correctness is often hard to assess from surface appearance alone: a shape may look plausible while remaining structurally wrong, non-editable, or unusable as supervision. As a result, many generated outputs are noisy, brittle, and difficult to curate at scale.

In this work, we argue that the key difficulty is not only how to generate CAD, but how to **reformulate CAD generation into a problem that can be verified precisely and curated efficiently**. Our central observation is that CAD is unusually well suited for this transformation: many CAD artifacts can be represented as executable programs, and executable programs naturally admit strong validation signals. Instead of treating CAD generation as open-ended geometry synthesis, we cast it as **verifiable program synthesis**. A model generates a CAD program, the program is executed into geometry, and the resulting artifact is validated with geometric overlap, rendered multi-view comparisons, and metadata consistency checks. This turns an otherwise weakly supervised generative problem into one with explicit acceptance criteria.

A second challenge is systems design. In practice, complex engineering data generation is poorly served by a single rigid workflow. Different samples fail for different reasons: some require stronger code synthesis, others need targeted repair, and the hardest cases benefit from explicit human checking. We therefore organize the process as a collection of reusable **skills** rather than a monolithic pipeline. These skills handle generation, execution, verification, repair, and dataset assembly, and can be composed, replaced, or extended independently. This modular design reduces maintenance cost, improves robustness to heterogeneous failure modes, and makes it easier to integrate manual inspection where high precision matters most.

Based on these ideas, we present a **skill-based, verification-guided CAD data generation framework** that transforms noisy generations into **verified program–geometry pairs** and packages them into training-ready supervision. Because full downstream CAD training is computationally expensive, our goal in this paper is not to claim a stronger trained generator, but to establish a practical and scalable method for constructing high-precision supervision from noisy outputs. The result is a data-centric view of CAD generation: verification acts not only as evaluation, but as the core curation mechanism that makes complex engineering data generation tractable.

### Contributions

Our contributions are fourfold.

First, we reformulate complex CAD generation as **verifiable program synthesis** rather than direct open-ended geometry generation.

Second, we introduce a **verification-guided curation pipeline** that executes generated CAD programs and filters them through geometric, visual, and metadata-based checks.

Third, we propose a **skill-based modular system** that replaces brittle rigid workflows with reusable components for generation, verification, repair, manual checking, and dataset assembly.

Fourth, we demonstrate that this design can convert noisy CAD generations into **high-precision, training-ready supervision**, and we evaluate it through data quality, verifier precision, and hard-case recovery without requiring downstream retraining.

---

# 六、Related Work 改成更贴 4 图的版本

## 2. Related Work

### 2.1 Parametric and Sequential CAD Generation

Prior work has shown that CAD objects can be represented as ordered construction procedures rather than only final shapes. This line of research models CAD as sketches, operations, and parameters, making generation more faithful to real engineering design. However, most such approaches still focus on direct generation quality rather than scalable curation of verified outputs.

### 2.2 Code-Oriented CAD Modeling

Recent methods increasingly treat CAD as a code-like domain, where outputs are structured commands with execution semantics. This perspective aligns naturally with language models and motivates using executable programs as the intermediate representation for CAD generation. Our work builds on this observation, but shifts the focus from generation alone to **verifiable program synthesis for data construction**.

### 2.3 Validation and CAD Quality Assessment

CAD quality cannot be reliably judged by appearance or token matching alone. Structural validity, geometric agreement, and engineering usability all matter. Prior work has proposed richer geometric and topological metrics, but validation is typically used as a post hoc evaluation tool. In contrast, our framework elevates verification to the role of **data filter and curation engine**.

### 2.4 Data-Centric Loops and Modular Systems

Our work is also related to data-centric machine learning systems that emphasize curation, filtering, and iterative improvement rather than generator design alone. We argue that complex engineering generation particularly benefits from **modular skill composition**, because heterogeneous failure modes are difficult to handle with a single rigid workflow. This leads to a more robust and extensible system for verified data generation.

---

# 七、Method 改成强对应 4 图的版本

## 3. Method

### 3.1 From Complex CAD Generation to Verifiable Program Synthesis

We begin with a simple observation: direct CAD generation is difficult because correctness is hard to assess in an open-ended output space. We therefore reformulate the task as generation of an **executable CAD program**. Once a program can be executed deterministically, its output can be compared against the target artifact through downstream validation signals. This problem reformulation is illustrated in **Figure 1**.

### 3.2 Verification-Guided CAD Data Curation

Our main pipeline is shown in **Figure 2**. Given a target example and associated structured inputs, the system first generates a CAD program. The program is then executed into a geometric artifact. The resulting artifact is passed through multiple validators, including geometric agreement checks, optional rendered-view comparison, and metadata consistency checks. Samples that satisfy strict acceptance criteria are stored as verified pairs; failed samples are discarded or routed to repair.

### 3.3 Skill-Based Modular System

A key design principle of our framework is that complex engineering data generation should not be implemented as a single rigid workflow. Instead, we decompose it into reusable **skills**, including generation, execution, verification, repair, manual checking, and dataset assembly. As shown in **Figure 3**, this modular design better handles heterogeneous failure modes, allows provider substitution, and makes it easier to recover hard-tail cases without redesigning the entire system.

### 3.4 Repair, Manual Checking, and Verified Storage

Some difficult examples fail automated generation despite strong validation signals. Rather than discarding these cases entirely, we include targeted repair and manual checking as first-class parts of the system. Recovered examples are stored together with provenance and validation metadata in a canonical verified representation. This produces a reusable store of **high-precision, training-ready program–geometry pairs**.

### 3.5 Training-Free Evaluation

Because full downstream CAD retraining is expensive, we evaluate the framework directly as a data engine. We focus on overall data quality, verifier precision, hard-case recovery, and complexity-aware coverage. Representative examples of accepted, rejected, and repaired outputs are shown in **Figure 4**.

---

# 八、Experiments 也按 4 图改

## 4. Experiments

### 4.1 Evaluation Setup

We evaluate the system without downstream retraining. Our goal is to determine whether noisy CAD generations can be converted into high-precision, reusable supervision.

### 4.2 Overall Pipeline Quality

Report:

* execution success rate
* verification pass rate
* final verified set size
* average IoU of accepted samples

这节呼应 Figure 2。

### 4.3 Effect of Repair and Manual Checking

Report:

* auto only
* auto + repair
* auto + repair + manual checking

这节呼应 Figure 3。

### 4.4 Qualitative Case Studies

Show:

* successful accepted case
* failed then repaired case

这节直接放 Figure 4。

### 4.5 Discussion of Training Readiness

Discuss:

* executability
* strict geometric agreement
* metadata completeness
* why these are useful proxies for future supervised learning

---

# 九、Discussion 也改成更贴图

## 5. Discussion

第一段回 Figure 1：

* 为什么“problem reformulation”是核心，不只是 pipeline engineering

第二段回 Figure 2：

* 为什么 verification 是 curation mechanism，不只是 evaluation metric

第三段回 Figure 3：

* 为什么 heterogeneous failure modes 需要 skill-based modularity

第四段回 Figure 4：

* 为什么 qualitative recovery on hard cases matters

最后写 limitation：

* no downstream training
* current validators may miss some semantic errors
* manual checking still needed on hardest tail

---

# 十、Conclusion 改成一句更稳的

## 6. Conclusion

We presented a skill-based, verification-guided framework for CAD data generation. By converting complex CAD generation into verifiable program synthesis, and by organizing the system around reusable skills rather than a rigid workflow, we transform noisy generations into high-precision, training-ready supervision. Our results suggest that, for complex engineering tasks, executable representations and strong verification provide a practical path toward scalable data curation.

---

# 十一、每张图在文中怎么引用最顺

## Figure 1

放在 Introduction 第 3 段附近
配一句：

> As illustrated in Figure 1, we do not directly optimize open-ended geometry generation; instead, we reformulate the task as executable and verifiable program synthesis.

## Figure 2

放在 Method 开头
配一句：

> Figure 2 shows the core curation loop of our framework: generate, execute, verify, repair, and store.

## Figure 3

放在 Method 后半段
配一句：

> Figure 3 highlights our key systems insight: robust CAD data generation requires reusable skills rather than a single brittle workflow.

## Figure 4

放在 Experiments / qualitative results
配一句：

> Figure 4 presents representative examples showing how verification and repair convert noisy generations into usable supervision.

---

# 十二、现在这篇文章最像 CVPR 的写法

你现在最该避免的是：

* 一上来写 implementation details
* 把 skill 写成工程脚本系统
* 把 paper 写成 dataset collection note

你最该坚持的是：

* **Figure 1 是问题重构**
* **Figure 2 是方法机制**
* **Figure 3 是系统 insight**
* **Figure 4 是可视化证据**

这就很像一篇 CVPR workshop paper 了。

下一步最值的是我直接继续帮你写：
**Figure 1–4 的 caption、每张图在文中的过渡段、以及一个完整的 8 页 section-by-section 骨架。**
