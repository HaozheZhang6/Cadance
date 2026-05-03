# Paper Outline

## Core Narrative

Existing CAD benchmarks largely focus on toy geometry and simple construction sequences. They do not sufficiently cover industrially meaningful part families, complex CAD operations, or the engineering constraints required by executable and editable parametric CAD programs.

We introduce an industrial CAD benchmark built around standard-inspired parametric part families. The benchmark evaluates large multimodal models on CAD generation, CAD understanding, and CAD editing. Beyond geometry similarity, it measures whether models produce executable code, recover functional features, use appropriate CAD operations, and preserve engineering constraints.

The central message of the paper is:

> Existing CAD benchmarks ask whether models can make simple shapes. Our benchmark asks whether models can generate executable, editable, operation-rich CAD programs for standard-inspired industrial parts.

The training result should be framed as a diagnostic finding rather than the main algorithmic contribution:

> CAD-specific training improves rare and advanced operation coverage, but current models still struggle with compositional industrial CAD reasoning.

## 1. Introduction

Large language models and multimodal models have made rapid progress in code generation, visual understanding, and 3D reasoning. However, CAD remains a challenging and under-evaluated domain. A valid CAD output is not merely a visually plausible shape. It should be executable, editable, parameterized, and consistent with engineering constraints.

Current CAD benchmarks often emphasize simple primitives, such as boxes, cylinders, extrusions, cuts, and basic boolean operations. These examples are useful, but they do not reflect the complexity of industrial CAD workflows, where geometry is defined by functional features, standard parameters, and multi-step construction operations.

This paper addresses three gaps:

1. Industrial relevance gap: existing benchmarks underrepresent engineering part families such as involute gears, twist drills, handwheels, shafts, fasteners, and other standard-inspired components.

2. Operation complexity gap: existing datasets are often dominated by simple sketch-extrude patterns and provide limited coverage of advanced operations such as revolve, sweep, helix, fillet, chamfer, arrays, threads, and gear-tooth construction.

3. Evaluation gap: geometry metrics alone are insufficient. A generated CAD program must execute, preserve intended features, use appropriate operations, and satisfy parameter-level engineering constraints.

The contributions can be written as:

1. We introduce an industrial CAD benchmark built from standard-inspired parametric part templates.

2. We design evaluation tasks covering CAD generation, CAD understanding, and CAD editing.

3. We benchmark open and proprietary multimodal models and show that current models remain far from solving engineering-grade CAD reasoning.

4. We introduce operation-level metrics, including rare operation recall, to evaluate whether models learn advanced CAD construction patterns.

5. We provide SFT and RL reference training baselines showing that CAD-specific training improves operation coverage, while compositional generalization remains a major challenge.

## 2. Related Work

### 2.1 CAD and 3D Generation Benchmarks

This section should position the benchmark against prior CAD and 3D generation datasets, including DeepCAD, Fusion360-style CAD history datasets, Text2CAD-style benchmarks, image-to-CAD or 3D-to-CAD reconstruction work, and general 3D generation benchmarks.

The key distinction is not that prior work is unimportant, but that it targets different aspects of the problem. Many existing datasets focus on CAD sequence modeling, geometry reconstruction, or text-conditioned generation. They usually provide limited coverage of industrial part families, operation-rich parametric construction, and engineering constraint evaluation.

This section should motivate Table 1, which compares datasets along axes such as industrial part families, executable code, multimodal inputs, editing tasks, operation annotations, rare operation coverage, and standard-inspired parameter constraints.

### 2.2 MLLM Evaluation for Code, 3D, and Engineering Reasoning

CAD code generation is not ordinary code generation. It requires spatial reasoning, geometric construction, feature planning, and engineering parameter consistency. This section should connect the paper to broader work on multimodal model evaluation, code generation benchmarks, 3D reasoning, and scientific or engineering reasoning.

### 2.3 Domain-Specific Training for CAD

This section should frame SFT and RL as domain adaptation tools. The paper does not need to claim a new general-purpose training algorithm. Instead, the training experiments are diagnostic: they test what models can learn from operation-rich industrial CAD data and where they still fail.

## 3. IndustrialCAD-Bench

This section should introduce the benchmark and include Figure 1.

Figure 1 should show the full pipeline:

```text
Industrial standards / engineering specifications
        ->
Parametric CAD templates
        ->
Ground-truth CadQuery code
        ->
STEP / mesh / renders / point clouds / metadata
        ->
Tasks: generation, understanding, editing
        ->
Evaluation: execution, geometry, features, operations, constraints
```

The key sentence for this section:

> Unlike primitive-centric CAD datasets, IndustrialCAD-Bench is organized around engineering part families whose geometry is defined by functional features and parameter constraints.

This section should explain:

1. What part families are included.

2. What input modalities are provided, such as single-view images, multi-view images, point clouds, code context, metadata, and edit instructions.

3. What outputs are expected, such as CadQuery code, parameter answers, feature-level answers, or edited CAD programs.

4. Why the benchmark is industrially meaningful.

5. Why it is suitable for evaluating large multimodal models.

## 4. Dataset Construction and Statistics

This section should correspond to Figure 2.

### 4.1 Parametric Part Templates

Describe how each part family is constructed from standard-inspired engineering parameters and procedural templates.

Examples:

```text
Involute gears: module, tooth count, pressure angle, pitch diameter, bore diameter.
Twist drills: diameter, flute length, helix angle, point angle, shank diameter.
Handwheels: rim diameter, spoke count, hub diameter, bore size, handle geometry.
```

Use "standard-inspired" unless the implementation strictly validates all requirements of a named standard. "Standard-compliant" should only be used when the generated parts are verified against the relevant standard.

### 4.2 Data Modalities

Each CAD program can be paired with:

1. Ground-truth CadQuery code.

2. Rendered images or multi-view images.

3. Point clouds.

4. Mesh, STL, or STEP files.

5. Metadata.

6. Operation annotations.

7. Feature annotations.

8. Parameter annotations.

### 4.3 Dataset Statistics

Figure 2 can include:

1. Part family distribution.

2. Operation distribution.

3. Advanced and rare operation ratio.

4. Average code length.

5. Average feature count.

6. Easy, medium, and hard examples.

The section should define operation categories used later in the paper:

```text
Basic operations: sketch, line, circle, extrude, cut.
Intermediate operations: revolve, fillet, chamfer, mirror, array.
Advanced or rare operations: sweep, loft, helix, thread, involute gear construction.
```

## 5. Tasks and Evaluation Protocol

This section should define the benchmark tasks and metrics.

### 5.1 CAD Generation

Input: image, multi-view image, point cloud, or combined multimodal input.

Output: executable CadQuery code.

Metrics:

```text
Execution pass rate
IoU
Chamfer distance
Feature F1
Operation recall
Rare operation recall
Standard or constraint compliance score
```

### 5.2 CAD Understanding

Input: render, point cloud, code, metadata context, or combined inputs.

Output: part family, parameters, functional attributes, feature counts, or answers to CAD-specific questions.

Example questions:

```text
What is the likely part family?
How many teeth does the gear have?
Which operation creates the central bore?
Does the drill contain helical flutes?
Is the bore diameter consistent with the specified shaft size?
```

Metrics:

```text
Accuracy
Exact match for discrete parameters
Numerical error for continuous parameters
Semantic correctness
Constraint judgment accuracy
```

### 5.3 CAD Editing

Input: original CAD code or shape representation plus an edit instruction.

Output: edited executable CAD code.

Example edits:

```text
Increase the bore diameter while preserving the tooth count.
Change the handwheel from three spokes to five spokes.
Add a keyway to the shaft.
Increase the drill flute length without changing the shank diameter.
```

Metrics:

```text
Edit success
Non-target preservation
Execution pass rate
Geometry consistency
Feature correctness
Constraint preservation
```

The main evaluation principle:

> We evaluate not only whether the generated geometry looks similar, but also whether the program uses the intended CAD construction operations and preserves engineering constraints.

## 6. Main Benchmark Results

This section should contain Figure 3 and Tables 2 to 4.

Recommended table structure:

```text
Table 2: CAD generation leaderboard.
Table 3: CAD understanding leaderboard.
Table 4: CAD editing leaderboard.
```

Figure 3 can show an overall leaderboard using a weighted score over generation, understanding, and editing. The text should not rely only on the overall score. It should separately discuss the three task groups.

### 6.1 Overall Performance

The main finding should be:

> Current multimodal models remain far from solving industrial CAD generation and editing.

### 6.2 Proprietary and Open Models

If the benchmark includes GPT, Gemini, Claude, Qwen, InternVL, LLaVA, or other models, compare them carefully:

1. Proprietary models may perform better on visual understanding and instruction following.

2. Open models may sometimes produce more stable code formatting after CAD-specific adaptation.

3. All model families remain weak on advanced operations and engineering constraint preservation.

### 6.3 Geometry Versus Program Correctness

A key result should be:

> Some models produce visually plausible geometry but fail to generate editable or operation-faithful CAD programs.

This finding justifies the benchmark design. Rendering-based similarity can hide failures in CAD construction logic.

## 7. Per-Task Analysis

This section should correspond to Figures 4 to 6.

### 7.1 Generation Analysis

Figure 4 can report execution pass rate, IoU or Chamfer distance, Feature F1, Operation Recall, and Rare Operation Recall.

Expected conclusion:

> Models often recover coarse shape but fail on feature completeness and operation-faithful construction.

Examples:

1. A generated gear has a plausible outer shape but the wrong tooth count.

2. A generated drill contains a cylinder and conical tip but lacks helical flutes.

3. A generated handwheel has a rim but misses or miscounts spokes.

### 7.2 Understanding Analysis

Figure 5 can split results by question type:

```text
Part classification
Parameter recognition
Feature counting
Function reasoning
Standard or constraint compliance judgment
```

Expected conclusion:

> Models can often recognize common part categories, but struggle with parameter-level and constraint-level reasoning.

### 7.3 Editing Analysis

Figure 6 can report target edit success, non-target preservation, execution pass rate, feature preservation, and parameter consistency.

Expected conclusion:

> Models often perform the requested edit while accidentally changing unrelated features, indicating weak parametric control.

Examples:

1. Increasing the bore diameter also changes the gear outer diameter.

2. Adding a keyway accidentally changes tooth count.

3. Changing the number of handwheel spokes breaks the hub or rim geometry.

## 8. Operation-Level Analysis

This section should correspond to Figure 7 and is one of the strongest parts of the paper.

### 8.1 Operation Richness

Compare IndustrialCAD-Bench with existing CAD datasets using:

```text
Unique operation count
Average operations per program
Advanced operation ratio
Rare operation ratio
Operation entropy
```

Expected conclusion:

> Compared with existing CAD datasets, IndustrialCAD-Bench contains a higher fraction of advanced and rare CAD operations.

### 8.2 Rare Operation Recall

Compare base, SFT, and RL-trained models on operation-level metrics:

```text
Rare operation recall
Advanced operation recall
Operation F1
Operation entropy
Seen-family versus unseen-family rare operation recall
```

Expected conclusion:

> SFT significantly improves rare operation recall, showing that operation-rich industrial CAD data teaches models more advanced construction patterns. However, the remaining gap to ground truth shows that operation composition and constraint-aware parametric reasoning remain unsolved.

Recommended Figure 7 layout:

```text
Figure 7(a): Operation distribution compared with existing datasets.
Figure 7(b): Base versus SFT versus RL rare operation recall.
Figure 7(c): Seen-family versus unseen-family rare operation recall.
```

## 9. Training Reference Models

This section should correspond to Table 5.

The framing should be explicit:

> Training reference models is not the main contribution of the paper. It is a diagnostic experiment for understanding what operation-rich CAD data teaches current models.

Table 5 can include:

```text
Model | Exec Pass | IoU | Feature F1 | Op Recall | Rare Op Recall | Constraint Score | External Bench
Base
SFT
SFT + RL
```

Expected findings:

1. SFT improves code executability and operation coverage.

2. RL can further improve execution-based or geometry-based metrics if the reward is well aligned.

3. Improvements are smaller on unseen part families and unseen operation compositions.

4. CAD-specific adaptation may cause a mild degradation on general-purpose benchmarks, suggesting a specialization trade-off.

This section should avoid overclaiming. The correct claim is not that the trained model solves CAD generation. The stronger and more defensible claim is that the benchmark reveals both learnable operation patterns and persistent generalization failures.

## 10. Generalization and Memorization Analysis

This section can be standalone or merged into the training section depending on space.

Recommended splits:

```text
Seen family / unseen parameters: tests parameter generalization.
Unseen family: tests part-family generalization.
Unseen operation composition: tests compositional operation generalization.
External CAD subset: tests out-of-distribution robustness.
```

Expected conclusion:

> Training improves seen-family parameter generalization but remains weak on unseen families and unseen operation compositions.

This section is important because it addresses the reviewer concern that the models may simply memorize parametric templates.

## 11. Error Analysis and Case Studies

This section should provide qualitative evidence for why models fail.

Error categories:

```text
Invalid code
Wrong primitive
Missing feature
Wrong feature count
Wrong dimension
Wrong workplane
Wrong operation
Constraint violation
Over-simplified template
Edit leakage
```

Examples:

```text
Over-simplification: a twist drill is generated as a cylinder plus cone.
Wrong operation: gear teeth are approximated by random triangular cuts.
Constraint violation: module, tooth count, and pitch diameter are inconsistent.
Edit leakage: changing the bore diameter also changes the outer diameter.
Feature omission: a handwheel is generated without spokes.
```

This section should make the benchmark more interpretable. It shows not only which models score poorly, but also why they fail.

## 12. Limitations

The limitations should be direct and credible:

1. The dataset is procedurally generated from parametric templates and does not fully represent proprietary industrial CAD repositories.

2. The benchmark is standard-inspired rather than fully standard-compliant unless each part is explicitly validated against a named standard.

3. The SFT and RL models are reference baselines rather than general-purpose state-of-the-art CAD models.

4. Automated metrics cannot fully replace expert review for manufacturability and design intent.

5. Some feature and constraint metrics require template-specific rules.

## 13. Conclusion

The conclusion should restate the main contribution and finding:

> We introduced an industrial CAD benchmark for evaluating executable, editable, operation-rich CAD programs. Experiments show that current multimodal models can sometimes recover coarse shapes and common part semantics, but they remain weak at advanced operations, engineering constraints, and compositional CAD reasoning. CAD-specific training improves rare operation coverage, but the gap to robust industrial CAD generation remains substantial.

## Recommended Figures

```text
Figure 1: Benchmark overview.
Figure 2: Dataset statistics and examples.
Figure 3: Overall leaderboard.
Figure 4: Generation task analysis.
Figure 5: Understanding task analysis.
Figure 6: Editing task analysis.
Figure 7: Operation richness and rare operation recall.
Figure 8: Error taxonomy and qualitative case studies, optional.
```

## Recommended Tables

```text
Table 1: Existing dataset and benchmark comparison.
Table 2: CAD generation leaderboard.
Table 3: CAD understanding leaderboard.
Table 4: CAD editing leaderboard.
Table 5: Training reference model results.
Table 6: Generalization split results, optional.
Table 7: External benchmark sanity check, optional.
```
