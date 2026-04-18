---

# Figure Captions and Body Text (based on figure_1/2/3.png)

---

## Figure 1 Caption

**Figure 1.** CADLoop overview. Raw 3D CAD geometry is first mapped from its non-Euclidean surface representation into a structured Euclidean form: a semantic geometry JSON encoding sketch planes, arc parameters, and extrusion constraints, paired with executable CadQuery source code. A VLM-based agent synthesizes, executes, and refines this output inside a verification feedback loop. The critical design choice is that the JSON's geometric parameters — arc center, reference vector, sweep angle, sketch-plane orientation — are not treated as opaque targets but as computable quantities. Skills give the agent direct access to these values, enabling it to calculate the correct arc midpoint or coordinate sign rather than estimating it from the raw shape.

---

## Figure 2 Caption

**Figure 2.** Comparison of baseline and CADLoop pipelines. **(A)** The baseline maps raw 3D geometry directly to code in a single, tool-free step. The agent receives no structured intermediate representation and has no means to verify or correct its output. **(B)** CADLoop separates generation from verification. A lightweight VLM-agent handles the common case; a rule-based verifier computes an exact IoU signal. When the verifier rejects an output, the system escalates to a VLM-agent equipped with skills, which can assign a diagnosis, step in to inspect the geometric record, and compute a targeted fix. The escalation path is the critical difference: the baseline retries blindly; CADLoop resolves the underlying geometric error by computation. The "Geometric Constraint Discovery" module feeds the structured arc/plane parameters that make this computation possible.

---

## Figure 3 Caption

**Figure 3.** Skill-driven geometric grounding, illustrated on the arc direction failure case. **(Top — Input and Bug Analysis)** A sub-agent generates CadQuery code that places the inner arc midpoint at (0.0, −90.0); the verifier returns IoU = 0.893 < 0.99, flagging the code as wrong. The erroneous line is highlighted in red. **(Middle — Reasoning and Geometric Grounding Flow)** The repair skill retrieves the Fusion360 JSON for the arc: center (0, −7) cm, radius 2 cm, reference vector (1, 0), sweep 0 → π. It applies the midpoint formula $p_\text{mid} = p_\text{center} + r \cdot \text{rotate}_\text{CCW}(\hat{v},\, \pi/2) = (0, -70) + 20 \cdot (0, 1) = (0, -50)$ and confirms the arc bows upward. An area check validates the diagnosis: the correct hole area is $140 \times 40 - \pi \times 20^2/2 = 4972\ \text{mm}^2$ (rectangle minus semicircle); the bad code produces a $+628\ \text{mm}^2$ excess, removing $87{,}920\ \text{mm}^3$ of extra material, which predicts exactly IoU ≈ 0.893. **(Bottom — Validated Output and Synthesis)** Replacing (0.0, −90.0) with the computed value (0.0, −50.0) fixes the profile; IoU rises to 0.999. The skill does not retry or rephrase — it computes the correct value from the geometric record.

---

## Body text: Introduction paragraph (insert after "small local mistake" sentence)

The difficulty is not syntactic. A language model trained on CadQuery code knows perfectly well how `threePointArc` works. The difficulty is that reconstructing a precise arc profile requires resolving quantities the model cannot reliably estimate from raw geometry: whether a sketch's local Y-axis maps to world $+Z$ or $-Z$; whether a semicircular hole bows into or away from the enclosing rectangle; whether a 146° arc's midpoint lies at the center or at $c + r \cdot \text{rotate}(\hat{v},\, 73°)$. These are deterministic geometric facts, not matters of generation quality. They are computable — but only when the agent has access to the structured JSON record and the skill to apply the relevant formula. Figure 1 illustrates the key architectural choice: rather than mapping raw geometry blind to code (Figure 2A), CADLoop exposes the geometric record to a skill-equipped agent (Figure 2B) that can ground its reasoning in exact values, not estimates.

---

## Body text: Section 3.4 paragraph (skills vs workflow, replaces last paragraph)

The advantage of skills over a general flexible workflow is most visible on the hard tail of the failure distribution. A workflow can reroute a failing sample to a different model or a different prompt; a skill can resolve it by computing the right answer. Figure 3 makes this concrete: no reprompting strategy recovers the midpoint (0, −50) unless the agent is given access to the arc JSON and the rotation formula. The same is true for every other recurring failure mode in our dataset. XZ-plane sign errors are fixed by reading the sketch's `x_axis` field and negating the profile's Y-coordinates — a one-line rule, not a heuristic. `both=True` distance errors are fixed by checking the `is_full_length` flag and halving the extrusion depth. `NewBody` mismatches are resolved by filtering the timeline to the last `JoinFeature` entry. Each is a **computable diagnostic**: the skill layer makes this computation available where a generic workflow would offer only rerouting. This is why, in a domain as geometrically constrained as CAD, skill-based composition produces higher hard-case recovery than workflow flexibility alone.

---

**最新决定：共 5 张图**
- Figure 1: Teaser 概念图
- Figure 2: Pipeline 流程图
- Figure 3: Skill vs workflow 对比图
- Figure 4: 自动通过的 case（Case A，多个）
- Figure 5: 修复前后对比（Case B，多个，before/after）

---

原始笔记（4 张图版本，已升级为 5 张）：

可以。按原 **4 张图** 来排，现在扩展为 5 张：

## 图 1：Teaser / 主概念图

**目的：一眼讲清整篇论文在做什么。**

### 应该放的内容

三段式，从左到右：

**左边：复杂 CAD 生成为什么难**

* 长链条构造
* 局部错误会级联
* 直接生成很脆弱
* 最好配一个复杂零件的 4-view 小图或轮廓示意

**中间：我们的核心重构**

* 不直接生成最终几何
* 改成生成 **可执行 CAD code / program**
* 程序执行后得到 geometry
* 这里最好放一个短短的 code snippet 示意

**右边：最终得到什么**

* verified program–geometry pairs
* training-ready data
* 高精度筛选后的 supervision

### 图上要传达的一句话

**Complex generation → verifiable program synthesis → verified data**

### 为什么它重要

这是第一页最强的图。
审稿人看完这张图，应该立刻明白：
你不是在做普通 workflow，而是在做 **problem reformulation + data engine**。

---

## 图 2：Method overview / 验证闭环图

**目的：讲清楚方法是怎么工作的。**

### 应该放的内容

我建议是最核心闭环：

**Input**

* raw STEP / reconstruction JSON / optional rendered views

**Generate**

* LLM generates CAD program

**Execute**

* execute program to geometry / STEP

**Verify**

* geometry verification: IoU
* visual verification: 4-view render
* schema / metadata check

**Decision**

* pass → verified store
* fail → repair/manual check

**Output**

* verified pair record
* assembled training-ready corpus

### 视觉结构

最好是一个横向主流程 + 一个失败回路：

* 主流程向右
* fail 回到 repair，再回 verified

### 图上要传达的一句话

**Verification is not just evaluation; it is the curation mechanism.**

### 为什么它重要

这张图是全文最扎实的方法图。
比起“我们有很多模块”，这张图更强调你真正的方法机制。

---

## 图 3：Skill-based system vs rigid workflow

**目的：把你的独特点讲出来，解释为什么不是普通 pipeline。**

### 应该放的内容

建议左右对比。

### 左边：Monolithic workflow

画成一条固定链：

* input
* generation
* execution
* validation
* fail

标几个问题：

* brittle
* hard to extend
* poor hard-case handling
* one failure breaks the chain

### 右边：Skill-based modular system

画成若干 skill：

* generation skill
* execution skill
* verification skill
* repair skill
* manual check skill
* dataset assembly skill

再画它们和 verified store 的连接。

### 最好在右边标 4 个关键词

* reusable
* extensible
* robust
* handles hard-tail cases

### 图上要传达的一句话

**Modular skills handle heterogeneous failures better than a rigid workflow.**

### 为什么它重要

这张图专门服务你的卖点：
**便宜、可扩展、robust、有 manual check、适合复杂问题。**

它不是主方法图，而是“系统 insight 图”。

---

## 图 4：Case study / 真实例子图

**目的：让审稿人具体看到你到底在做什么。**

这张图很重要，我觉得比 training-free evaluation 图更值得放正文。

### 应该放的内容

建议做成 **2 个 case**，一个成功、一个失败后修复。

---

### Case A：直接通过的样本

四列：

**(1) Target**

* raw STEP 4-view

**(2) Generated program**

* 放 4–8 行最关键的 CadQuery code snippet

**(3) Generated geometry**

* generated STEP 4-view

**(4) Verification**

* IoU = 0.xxx
* visual check = pass
* status = accepted

---

### Case B：失败并修复的样本

四列同样结构：

**(1) Target**

* raw STEP 4-view

**(2) Initial generated program**

* 标出 bug 点，比如 wrong arc direction

**(3) Repaired geometry**

* 修复前后都可放
* 或者上排失败，下排修复后

**(4) Verification**

* before repair: IoU = 0.84, rejected
* after repair: IoU = 0.995, accepted

---

### 这张图的重点

一定要让人看到：

* 你处理的是 **真实复杂 CAD**
* verification 真的在区分好坏
* repair/manual check 真的能恢复 hard-tail case

### 图上要传达的一句话

**Concrete examples show how verification and repair turn noisy generations into usable supervision.**

---

# 如果是这 4 张图，全文故事顺序就是

## 图 1

**问题重构**

* 为什么直接做 CAD generation 很难
* 为什么改成 verifiable program synthesis

## 图 2

**核心方法**

* 生成、执行、验证、修复、存储的闭环

## 图 3

**系统设计原则**

* 为什么要 skills，不要 rigid workflow

## 图 4

**真实案例**

* 证明这不是抽象概念，是真能 work 的

---

# 每张图最理想的标题

你可以直接先用这些：

### Figure 1

**From Complex CAD Generation to Verifiable Data Generation**

### Figure 2

**Verification-Guided CAD Data Curation Pipeline**

### Figure 3

**Why Skill-Based Composition Instead of a Rigid Workflow**

### Figure 4

**Representative CAD Generation and Repair Cases**

---

# 每张图最关键的视觉元素

## Figure 1

* 复杂零件图
* code snippet
* verified pair / accepted stamp

## Figure 2

* pass/fail 分叉
* verifier 模块
* repair 回路

## Figure 3

* 左右对比
* rigid vs modular
* 4 个优点标签

## Figure 4

* raw vs generated vs repaired
* IoU 数字
* accepted / rejected 标记

---

# 一个很重要的小建议

4 张图里，**至少 2 张必须包含真实 CAD 视觉内容**，不要全是框图。
否则很容易显得太系统、太抽象。

所以我建议：

* Figure 1：可以半概念半真实
* Figure 2：流程图
* Figure 3：对比架构图
* Figure 4：真实 case 图

这样比例比较平衡。

---

# 最终推荐版

我建议正文就放这 4 张：

1. **主概念图**：复杂生成 → 可验证程序 → verified data
2. **方法闭环图**：generate → execute → verify → repair → store
3. **skill vs workflow 对比图**：解释你的系统 insight
4. **真实案例图**：展示成功样本和修复样本

下一步最值的是我直接帮你把这 4 张图的**版式草图和 caption 文案**一起定下来。
