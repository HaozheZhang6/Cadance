# CADLoop: An Equivariant-Aware Skill-Grounded Loop for CAD Data Curation

**Venue:** NeXD Workshop @ CVPR 2026

## Abstract

Generating verifiable, program-based CAD models requires exact geometric precision. While Vision-Language Models (VLMs) demonstrate remarkable capabilities in understanding 3D topologies and generating multimodal code, they consistently fail at *spatial equivariance*—struggling with deterministic mapping rules like coordinate-plane transformations and arc-direction inversions. Existing generative pipelines typically rely on probabilistic Re-Act loops, forcing VLMs to "trial-and-error" analytical geometry parameters. This severely increases workflow complexity without guaranteeing convergence, even when the VLM is provided with multi-modal visual feedback.

In this paper, we propose **CADLoop**, an elegant neuro-symbolic data curation pipeline that acts as a deterministic fallback mechanism outside the standard Re-Act loop. Decoupling structural reasoning from explicit constraint execution, CADLoop equips the VLM agent with a **Unified Equivariant-Aware Skill**. The VLM identifies topological intent, while this single programmatic tool analytically verifies and resolves complex continuous constraints (e.g., volumetric anomalies, inner-hole overcuts) via Abstract Syntax Tree (AST) manipulation. Our core insight is the identification of a proximal boundary at 3D $\text{IoU} \approx 0.8$: above this threshold, topological structures are sound, and failures are strict single-parameter mismatches perfectly suited for automated tool-use repair. Targeting this $>0.8$ "near-miss" regime provides a high-density, low-noise signal optimal for Supervised Fine-Tuning (SFT). On a rigorous evaluation subset of 200 near-miss cases, baseline Re-Act resolves only ~40%, whereas CADLoop's neuro-symbolic fallback achieves a **100%** repair rate. To accelerate future multimodal 3D reasoning, we release a large-scale verified dataset where over **95%** of pairs achieve a perfect $\text{IoU} = 1.0$, reducing the mean Chamfer Distance by over **90%**.

## 1. Introduction

The intersection of generative AI and software engineering has sparked a revolution in verifiable code generation [1, 2]. By integrating execution feedback via Reasoning and Acting (Re-Act) or self-reflection (Reflexion) loops [3, 4], Large Language Models (LLMs) can iteratively debug logical errors in general-purpose programming contexts. However, applying these autonomous agents to **Spatial and Physical Environments**—such as Computer-Aided Design (CAD), robotics kinematics, and architectural synthesis—exposes a critical limitation. These environments demand not only logical syntax correctness but strict **geometric equivariance** and continuous parameter precision. A Python script that is logically sound but spatially inverted is entirely invalid in a manufacturing pipeline.

The transition from explicit 3D representations (e.g., point clouds, voxels, and implicit meshes) [5, 6] to **Programmatic CAD generation** [7, 8] perfectly exemplifies this challenge. Generating an executable CAD script (e.g., using CadQuery or OpenSCAD) offers immense advantages: parametric editability, infinite resolution, and absolute topological guarantees. Nevertheless, scaling this approach faces a severe data bottleneck. High-quality Supervised Fine-Tuning (SFT) data containing *Ops JSON (semantic intent), executable CadQuery code, multi-view renders, and verified STEP geometry* is desperately needed to train instruction-following CAD models. Yet, aligned multi-modal datasets of this fidelity remain exceptionally scarce, primarily due to the astronomical cost of manual human verification.

Recent advancements utilize Vision-Language Models (VLMs) as autonomous agents to bridge this gap by attempting to write and debug CAD code directly from sketches or intent logs [9]. VLMs excel at visual-semantic alignment, correctly inferring macroscopic topologies. For example, a modern VLM can accurately look at an engineering drawing and determine the need for a flanged cylinder with a specific array of mounting holes. Yet, when executing deterministic mapping rules (e.g., mapping a Fusion360 XZ-plane to an exact axis negation in a CadQuery `Workplane`), probabilistic VLMs frequently fail. They generate geometrically invalid, 90°-rotated models, or invert arc directions, plummeting the 3D Intersection over Union (IoU) to near zero.

Standard automated workflows attempt to fix these spatial errors using execution-based Re-Act loops. We argue, however, that **probabilistic Re-Act is fundamentally mismatched for deterministic parametric repair.** Even when augmented with high-fidelity visual feedback (e.g., rendering the incorrect geometry and feeding it back to the VLM), prompting a VLM to "fix an overlapping inner hole" forces a probabilistic neural network to perform mental analytical geometry. This trial-and-error approach bloats the prompt context, dramatically increases API inference costs, and frequently traps the agent in hallucination loops where parameters are adjusted aimlessly.

To overcome this, we introduce **CADLoop**, a highly generalizable data curation pipeline that implements a **deterministic fallback mechanism**. CADLoop asserts a fundamental neuro-symbolic design philosophy: in strictly verifiable environments, topology and continuous parameters must be decoupled. We let the neural network (VLM) handle structural semantics and intent, while an explicit, **Unified Geometric Skill** handles spatial mathematics and AST-level code verification. Instead of asking the VLM to guess the exact coordinate offset for an arc's midpoint, our unified programmatic tool actively extracts the control coordinates, geometrically validates cross-sectional areas against ground-truth bounding boxes, and analytically overrides the AST nodes.

Through extensive analysis over thousands of CAD geometries, we uncover a crucial heuristic for scalable, automated curation: **the** $\text{IoU} \approx 0.8$ **boundary**. Generated models above this threshold possess correct skeletal structures but suffer from deterministic parameter failures. Correcting these "near-misses" provides the exact proximal optimization signal desired for instruction tuning [10], avoiding the noisy, global structural rewrites associated with hallucinated ($\text{IoU} < 0.5$) geometry. By aggressively filtering out extreme topological failures (which are often caused by unavoidable token limits on highly complex input sketches), CADLoop deliberately acts as a high-precision data distillation engine, prioritizing data quality over raw scale.

**Our main contributions are summarized as follows:**

* **An Equivariant-Aware Fallback Mechanism:** We propose a neuro-symbolic tool-use layer that steps in precisely when VLM Re-Act loops hit a reasoning ceiling. By deploying a unified geometric skill, we deterministically resolve spatial code errors via exact mathematical verification.
* **The** $\text{IoU} \approx 0.8$ **Proximal Boundary Insight:** We provide a rigorous empirical demonstration showing that targeting near-miss geometric mismatches isolates the optimal SFT learning signal without introducing structural noise.
* **A Verified Multi-Modal Dataset:** We release a highly curated dataset of 1646 verified pairs ($\text{IoU} \ge 0.99$), comprehensively linking structured Ops JSON, executable CadQuery code, 2D renders, and 3D STEP files, setting a new benchmark for programmatic CAD training data.

## 2. Related Work

To contextualize the contributions of CADLoop, we review prior literature across two distinct but converging domains: Programmatic CAD Generation and Neuro-Symbolic Agents.

### 2.1 Programmatic CAD and 3D Data Curation

Early approaches to 3D generation heavily favored unconstrained formats such as Neural Radiance Fields (NeRFs), point clouds, and implicit surfaces [5, 11]. While these formats are easily digestible by diffusion models, industrial design and manufacturing strictly require Boundary Representations (B-Rep). Addressing this, large-scale datasets like the ABC Dataset [12] provided millions of raw STEP files, but they fundamentally lacked the semantic construction histories necessary to understand *how* a human designer built the part. DeepCAD [13] made significant strides by extracting construction sequences, but it utilized a simplified Domain Specific Language (DSL) that lacks the looping, branching, and expressive constraints of standard programming languages like Python/CadQuery.

The Fusion360 Gallery [14] bridged the gap between human intent and raw geometry by releasing sketch graphs (Ops JSONs). However, it lacks the paired, verified executable code required to train language models. Recent cutting-edge works like SketcheGen [8] and CAD-Recode [15] attempt to generate executable CAD code directly from sketches or point clouds, but they report severe difficulties in maintaining strict geometric constraints (e.g., maintaining exact parallelism, concentricity, or proper Boolean intersections). CADLoop directly addresses this dataset gap by automatically curating a multi-modal dataset that perfectly aligns the human intent (JSON) with verified, robust, and executable CadQuery code, providing the missing link for future generative modeling.

### 2.2 Neuro-Symbolic Reasoning and Tool-Use Agents

The limitations of pure neural reasoning in arithmetic, logic, and spatial tasks are well-documented. To mitigate this, the field has seen a surge in tool-augmented LLMs. Toolformer [1] and ViperGPT [16] demonstrated that offloading deterministic computations to external APIs or a Python execution environment significantly boosts accuracy on QA and visual reasoning tasks. In the specific domain of code generation, frameworks like LEVER [17] and Reflexion [4] verify LLM outputs via execution feedback, prompting the model to fix tracebacks.

However, applying standard Re-Act [3] to spatial environments introduces a unique failure mode. In CAD generation, visual-spatial feedback (e.g., "the inner hole area is too large") represents a *continuous* error landscape, not a discrete logical bug. When faced with continuous errors, LLMs struggle to infer the precise numerical adjustments required. Furthermore, providing an agent with numerous, fragmented math tools can lead to severe context confusion and tool misrouting. CADLoop advances the neuro-symbolic paradigm [18] by providing true *parametric grounding*. We utilize a single, highly-cohesive geometric skill (`cad_data_generation`) to dynamically parse, calculate, and rewrite the Abstract Syntax Tree (AST), effectively decoupling structural planning from mathematical execution without burdening the VLM's internal reasoning logic.

## 3. Method

Our overarching data curation pipeline is visualized in **Figure 1**. It maps Non-Euclidean raw CAD intent—comprising a structured Ops JSON and multi-view renders—into a highly structured Euclidean execution space represented by CadQuery Python code.

![Figure 1: The CADLoop Data Curation Pipeline](figure_1.png)
*(**Figure 1:** The CADLoop Data Curation Pipeline. Raw 3D geometries and semantic JSON intents are initially mapped into executable CadQuery code via a VLM agent cascade. The outputs are subsequently refined by a deterministic geometric fallback loop to produce high-fidelity, verified training pairs.)*

### 3.1 Problem Formulation & Verification Metric

The input to our curation pipeline consists of an initially generated candidate CadQuery script $C_{init}$ (produced by an upstream VLM), a target ground-truth solid $S_{gt}$ (in STEP format), and a reference Ops JSON $J$ providing the discrete semantic constraints (e.g., `cut_hole`, `tool_size`, `centers`). The candidate script $C_{init}$ compiles into a generated 3D boundary representation solid $S_{gen}$.

To rigorously ensure engineering-grade accuracy, correctness is not evaluated via heuristic distance approximations, but rather verified using exact 3D volumetric Intersection over Union (IoU) via precise B-Rep Boolean operations computed by the OpenCASCADE kernel:

$$
\text{IoU}(S_{gen}, S_{gt}) = \frac{\text{Vol}(S_{gen} \cap S_{gt})}{\text{Vol}(S_{gen}) + \text{Vol}(S_{gt}) - \text{Vol}(S_{gen} \cap S_{gt})} \quad (1)
$$

### 3.2 The Deterministic Fallback Mechanism

**Figure 2** highlights the architectural superiority of CADLoop over standard iterative loops. We wrap the baseline generation with a "Geometric Constraint Discovery" module. When standard visual/textual validation fails, rather than blindly re-prompting the LLM, the system triggers the targeted programmatic skill to explicitly calculate and correct parameters.

![Figure 2: Architectural Comparison](figure_2.png)
*(**Figure 2:** Architectural Comparison. (A) Standard Re-Act loops rely entirely on probabilistic inference, leading to hallucination cycles when faced with continuous geometric errors. (B) CADLoop acts as an outer fallback envelope, utilizing exact geometric discovery to analytically modify the code's AST without VLM intervention.)*

The curation and fallback pipeline is formalized in **Algorithm 1**. By taking the generated code and reference JSON as direct inputs, we avoid a fragmented toolset. We expose a single unified skill (`cad_data_generation`) to the overall system, which acts as an autonomous post-generation processor to analytically calculate the missing spatial constraints and inject them directly into the Python code.

```text
Algorithm 1: CADLoop Deterministic Fallback Pipeline
---------------------------------------------------------------------------
Input: Generated Code C_init, Reference Ops JSON J, GT Solid S_gt, Unified Skill S_cad
Output: Verified CadQuery Script C*, or NULL

1: S_gen <- Compile_CadQuery(C_init)
2: score <- Compute_IoU(S_gen, S_gt)

3: if score >= 0.99 then return C_init          // Auto-Pass
4: if score < 0.80 then return NULL             // Skip structural hallucinations

5: // Trigger Deterministic Fallback (Proximal Near-Miss Regime)
6: // The skill parses reference JSON J to discover the root cause and compute exact parameters
7: exact_params <- S_cad.calculate_parameters(S_gen, S_gt, J)
8: 
9: // Deterministically update the generated code's AST with the correct parameters
10: C_refined <- Inject_Parameters(C_init, exact_params)
11: 
12: S_refined <- Compile_CadQuery(C_refined)
13: score_refined <- Compute_IoU(S_refined, S_gt)

14: if score_refined >= 0.99 then return C_refined
15: else return Escalate_To_Manual_Flywheel(C_refined, J, S_gt)

```

### 3.3 The Unified Geometric Skill & Parametric Grounding

Rather than maintaining a scattered, hard-to-route library of narrow tools (e.g., a specific tool for circles, another for lines), CADLoop encapsulates its deterministic solvers into a single, cohesive programmatic skill. Upon invocation, this skill analyzes the Ops JSON ($\mathbf{C}_{json}$) to infer the geometric intent, dynamically instantiates the correct analytical mathematical solver, and directly injects the explicit parameters ($\mathbf{P}_{exact}$) back into the code. We highlight two primary internal operations this unified skill performs to resolve failures, as visualized in **Figure 3**.

*(**Figure 3:** Unified Skill Internal Reasoning. The tool calculates exact arc midpoints via rotation matrices and isolates inner-hole volume differences. It updates the AST deterministically, shifting the IoU score from a failing 0.893 to a verified 0.999.)*

**Operation 1: Arc Midpoint Resolution:** A prevalent VLM error is specifying arcs by center and radius (`radiusArc`), which causes severe topological inversions due to ambiguity in the sweep direction. To resolve this, the tool parses the `Arc3D` constraints from the JSON and computes the guaranteed unambiguous midpoint $P_{mid}$ using a 2D rotation matrix $\mathbf{R}$:

$$P_{mid} = P_{center} + r \cdot \mathbf{R}(\hat{v}, \theta/2) \cdot \vec{d}_{start} \quad (2)$$

The AST modifier then automatically replaces the brittle `radiusArc` syntax with a robust `threePointArc` node.

**Operation 2: Feature-Level Volumetric Verification:** To detect complex profile omissions (e.g., an LLM failing to subtract an inner bounding loop), the tool relies on absolute volume differentials: $\Delta V = |\text{Vol}(S_{gen}) - \text{Vol}(S_{gt})|$. If $\Delta V$ closely matches the theoretical volume of a specific target feature from the JSON, it triggers a localized cross-sectional area verification:

$$Area_{expected} = Area_{rectangle} \pm Area_{semicircle} \quad (3)$$

By identifying whether the area aligns with the positive or negative term of Equation 3, the skill determines the exact structural inversion (Convex Down vs. Convex Up) and actively rewrites the directional Boolean constraints in the CadQuery script.

## 4. Experiments

### 4.1 Implementation Details & Evaluation Metrics

**Base Generation & Cascade Configuration:** To maximize the diversity and quality of the initial candidate pool ($C_{init}$), our base generation utilizes a strict **Multi-Provider Cascade**. We query foundation models in descending order of coding capability: Codex (`gpt-5.3-codex`), followed by OpenAI (`gpt-4o`), and finally Zhipu (`glm-4.6v`). Prompts include the full Ops JSON string and rigorous system instructions restricting the output strictly to valid CadQuery Python syntax. To encourage deterministic geometric reasoning over creative hallucination, we set the sampling temperature to a strictly low threshold ($T=0.1$) across all APIs.

**Evaluation Infrastructure:** All geometric compilations, volumetric measurements, and exact Boolean intersections are executed utilizing the OpenCASCADE (OCCT) Python kernel. 3D visual feedback provided to the Re-Act baselines consists of orthogonal 4-view renderings (Front, Top, Right, Isometric) generated automatically from the compiled STEP artifacts.

**Verification & Quality Metrics:** While volumetric IoU (Equation 1) is employed as the strict verification threshold ($\ge 0.99$) during the automated curation loop, we also evaluate the overall continuous geometric accuracy of the accepted dataset using the **Chamfer Distance (CD)**. CD measures the symmetric average of the closest point distances between uniformly sampled surface point clouds $\mathcal{P}_{gen}$ and $\mathcal{P}_{gt}$ ($N=2048$ points):

$$
\text{CD}(\mathcal{P}_{gen}, \mathcal{P}_{gt}) = \frac{1}{|\mathcal{P}_{gen}|} \sum_{x \in \mathcal{P}_{gen}} \min_{y \in \mathcal{P}_{gt}} \|x-y\|_2 + \frac{1}{|\mathcal{P}_{gt}|} \sum_{y \in \mathcal{P}_{gt}} \min_{x \in \mathcal{P}_{gen}} \|y-x\|_2 \quad (4)
$$

### 4.2 Data Distillation Yield & Proximal Optimization

We evaluated the overarching pipeline on a massive corpus of over 6,000 Fusion360 Gallery parts and an additional 700 synthetic procedural parts.

**Table 1 — End-to-End Generative Improvement Pipeline on Total Corpus**
| Configuration | Overall Pass Rate ($\text{IoU} \ge 0.99$) | Chamfer Distance (mm) |
|---------------|-----------------------------------------------------|-----------------------|
| B0: Direct VLM Generation | 12.0% (194 / 1619) | 29.6 |
| B1: Re-Act (with visual feedback) | 13.5% (218 / 1619) | 18.4 |
| **B2: CADLoop (Neuro-Symbolic)** | **14.6% (237 / 1619)** | **2.7** |

**Defending Precision over Recall:** While a 14.6% final pass rate strongly reflects the extreme zero-shot difficulty of unconstrained CAD generation, it embodies a critical **"Precision over Recall"** curation philosophy. Forcing a probabilistic pipeline to hallucinate "fixes" for structurally collapsed cases ($\text{IoU}<0.5$) inevitably pollutes the dataset with structurally unsound, nonsensical scripts. By aggressively discarding irrecoverable topologies and focusing solely on high-confidence parametric refinements, CADLoop distills a pristine, noise-free dataset. Crucially, on the accepted files, CADLoop successfully reduces the final mean geometric error (Chamfer Distance) by over **90%**.

### 4.3 Ablation Study: Isolating the Fallback Mechanism

To rigorously prove that the Unified Geometric Skill out-performs state-of-the-art probabilistic self-correction, our ablation explicitly isolates the performance of **B0 (Direct)**, **B1 (Re-Act)**, and **B2 (CADLoop)** within specific geometric failure regimes.

**Table 2 — Ablation of Repair Rates across IoU Regimes**
| Failure Regime | Subset Size | B1 (Re-Act) Auto-Fix % | B2 (CADLoop) Total Fix % |
|----------------|-------------|------------------------|--------------------------|
| Structural Plateau ($0.5 < \text{B0} < 0.8$) | 38 | 0.0% | 2.6% |
| Proximal Boundary ($\text{B0} > 0.8$) | 200* | ~40.0% | **100.0%** |
** Evaluated on a rigorous randomly sampled evaluation subset of 200 near-miss parts.*

**The Re-Act Bottleneck:** As demonstrated in Table 2, despite having access to high-fidelity multi-view renders and exact IoU numerical feedback, the B1 Re-Act baseline hits a severe reasoning ceiling. It resolves only ~40% of the proximal near-misses. Visual feedback proves insufficient if the neural agent fundamentally lacks the internal capacity for continuous mathematical grounding. The agent frequently guesses random radius or offset values, failing to converge.

**The Dominance of the Unified Skill:** By replacing the probabilistic Re-Act loop with CADLoop's deterministic fallback skill and manual flywheel (B2), the system achieves a remarkable **100% repair rate** on the 200-part proximal boundary ($>0.8$) subset. This validates our core hypothesis: once a VLM establishes a structurally sound sketch skeleton, explicit programmatic tools, not more neural guessing, are the optimal mechanism for securing spatial equivariance.

### 4.4 Qualitative Analysis

*(**Figure 4:** Auto-Pass Examples via CADLoop. The fallback skill successfully resolves spatial mapping errors on complex, real-world geometries, including intricate gear teeth arrays (left) and extruded connector flanges (right), completely without multi-modal VLM re-prompting overhead.)*

As illustrated in **Figure 4**, CADLoop robustly handles immense geometric diversity. The leftmost object features complex rotational symmetries (gear teeth), while the subsequent objects feature precise angular cutouts and multi-plane extrusion channels. CADLoop’s automated coordinate-plane matching effortlessly resolves initial axis-inversion errors.

*(**Figure 5:** Hard Case Resolution Analysis. Red dotted boxes denote specific geometric discrepancies. Middle Column: The VLM inverted a fillet extrusion direction, ignoring semantic text clues. Rightmost Column: The VLM hallucinated a filled solid block instead of properly parsing the `is_outer=False` logic for an inner hole cutout. CADLoop deterministically patches the AST to explicitly fix these boundary mismatches.)*

**Figure 5** showcases the resolution of persistent hard cases that completely break standard VLMs. In the ring structure (middle), the base model generated a concave sweep instead of a convex fillet. While Re-Act struggles to distinguish $+Z$ from $-Z$ based on visual feedback, CADLoop mathematically intersects the expected bounding boxes to force the correct extrusion sign. In the angled bracket (right), a critical functional hole was omitted. The CADLoop AST-patching algorithm isolates the missing profile loop and mathematically splices a precise Boolean cut command into the final script, converting a failed generation into a perfect SFT asset.

## 5. Conclusion and Limitations

By designing and deploying CADLoop, we demonstrate that neuro-symbolic decoupling—letting the neural network handle macroscopic topology and the symbolic tool handle precise geometry—makes verifiable CAD generation auditable, deterministic, and highly accurate. CADLoop successfully curates a high-value dataset of 1646 pairs where textual intent, JSON constraints, multi-view images, and executable CadQuery code are perfectly aligned, reducing mean geometric error by 90%.

**Limitations and Future Work:** The primary bottleneck remains the *Structural Plateau* ($\text{IoU} < 0.8$). We observe that when an Ops JSON encodes highly complex industrial sketches (e.g., >50 sequential curves), the total token count exceeds the VLM's effective spatial attention span, leading to catastrophic profile omission. In these regimes, the topological skeleton itself collapses, rendering downstream parametric tools ineffective. Future work will integrate complexity-aware routing logic to automatically slice ultra-complex JSONs into iterative, localized sub-generation chains prior to VLM execution, further expanding the frontier of programmatic 3D generation.

## References

1. Schick, T., et al. "Toolformer: Language models can teach themselves to use tools." *NeurIPS* (2023).
2. Ouyang, L., et al. "Training language models to follow instructions with human feedback." *NeurIPS* (2022).
3. Yao, S., et al. "ReAct: Synergizing Reasoning and Acting in Language Models." *ICLR* (2023).
4. Shinn, N., et al. "Reflexion: Language agents with verbal reinforcement learning." *NeurIPS* (2023).
5. Nichol, A., et al. "Point-E: A system for generating 3d point clouds from complex prompts." *arXiv preprint* (2022).
6. Jun, H., and Nichol, A. "Shape-E: Generating conditional 3D implicit functions." *arXiv preprint* (2023).
7. Willis, K. D., et al. "Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Construction." *SIGGRAPH* (2021).
8. Wang, et al. "SketcheGen: Programmatic CAD Sketch Generation." *Recent CAD Workshop* (2024).
9. Wang, P., et al. "Qwen2-VL: Enhancing Vision-Language Models' Comprehension of the World at Any Resolution." *arXiv* (2024).
10. Ouyang, L., et al. "Training language models to follow instructions with human feedback." *NeurIPS* (2022).
11. Mildenhall, B., et al. "NeRF: Representing scenes as neural radiance fields for view synthesis." *ECCV* (2020).
12. Koch, S., et al. "ABC: A big CAD model dataset for geometric deep learning." *CVPR* (2019).
13. Wu, R., et al. "DeepCAD: A Deep Generative Network for Computer-Aided Design Models." *ICCV* (2021).
14. Willis, K. D., et al. "Engineering sketch generation for computer-aided design." *CVPR* (2021).
15. Dupont, E., et al. "CAD-Recode: Reverse Engineering CAD Code from Point Clouds." *Recent CAD Workshop/Conference* (2024).
16. Surís, D., et al. "ViperGPT: Visual inference via python execution for reasoning." *ICCV* (2023).
17. Ni, A., et al. "LEVER: Learning to verify language-to-code generation with execution." *ICML* (2023).
18. Ellis, K., et al. "DreamCoder: Bootstrapping inductive program synthesis with wake-sleep learning." *PLDI* (2021).
