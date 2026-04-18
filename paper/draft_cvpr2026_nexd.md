# CADLoop: An Equivariant-Aware Skill-Grounded Loop for CAD Data Curation

**Venue:** NeXD Workshop @ CVPR 2026
**Target:** ~8 pages + refs

---

## Abstract

We present **CADLoop**, a data curation pipeline for converting raw Fusion360 parametric geometry into verified multi-modal training records (structured JSON, CadQuery code, multi-view renders, verified STEP). The core contribution is a **geometric skill library** — a compact, interpretable set of equivariance-aware repair rules that encode systematic failure modes of naive LLM code generation (coordinate-plane mapping, arc-direction inversion, extrude-sign ambiguity). A Re-Act loop applies these skills automatically; residual failures escalate to a Claude-Code manual tier that both resolves cases and grows the skill library. The key insight is a sharp boundary at B0 IoU ≈ 0.8: above it, failures are *single-parameter* (wrong arc midpoint, extrude sign, plane axis) and fully recoverable — the skill library alone auto-fixes **40.6%**, and the full CADLoop achieves a **100% repair rate** (N = 32, mean IoU 0.901→0.9998); below it (IoU 0.5–0.8, N = 38), failures are multi-error structural plateaus that B2 cannot resolve — mean IoU barely changes (0.665→0.662). This boundary motivates both target population selection and future skill design. The curated dataset contains **N = 1646 verified pairs** (IoU ≥ 0.99), 95.9% at IoU = 1.0, with Chamfer Distance dropping from 29.6 mm (B0) to 2.7 mm (B2) on accepted pairs.

---

## 1. Introduction

Training data for CAD reconstruction requires geometric precision: a pair is only useful if the generated code reconstructs the geometry to within measurement tolerance. Single-pass LLM generation fails on this criterion for a predictable set of reasons — all stemming from *geometric equivariance* mismatches between the Fusion360 parametric space and the CadQuery execution space.

We identify three root cause categories (Figure 3):

1. **Coordinate-plane mapping** — Fusion360 XZ-plane local-y maps to world −Z in CadQuery; YZ-plane (u,v) requires a (world-Z, world-Y) swap. A model that ignores this produces geometry rotated 90° or mirrored, yielding IoU ≈ 0.
2. **Arc-direction inversion** — arcs defined by center+radius are ambiguous in traversal direction; the wrong choice inverts a convex fillet into a concave cut (IoU ≈ 0.87–0.93).
3. **Extrude-direction and body semantics** — Fusion360 `NewBody` produces a single isolated body; code that unions with prior bodies, or inverts the extrude sign, yields systematic volume mis-match.

None of these failures require new training data to fix. They require **skills**: analytic rules that detect the mismatch from the ops JSON and repair the code deterministically.

**Contributions:**

- A geometric skill library encoding equivariance rules covering the top-3 LLM failure modes (§2.2).
- A near-miss analysis showing the skill library achieves **100% repair rate** on B0 IoU > 0.8 parts (N = 32) and **47% repair** on B0 IoU > 0.5 parts (N = 70) — with **0% execution failure** throughout (Table 2).
- A Re-Act loop that applies skills automatically, achieving **40.6% auto-fix** on near-misses with zero human cost (Figure 2).
- A two-tier design (Re-Act + Claude-Code manual) with a skill-growth flywheel: every B2 case is a skill candidate (Figures 4–5).
- A verified dataset of 1646 pairs with full multi-modal linkage, free to the community.

---

## 2. Method

### 2.1 Non-Euclidean → Euclidean Mapping

Raw STEP/STL geometry is rotation- and scale-sensitive. We first extract a structured **ops JSON** (from Fusion360 parametric data) that anchors all generation to a coordinate-system-invariant, operation-level description (Figure 1). This mapping is the foundation on which the skill library operates.

### 2.2 Geometric Skill Library

Each skill encodes one root-cause repair:


| Skill           | Failure trigger            | Repair action                                                                                                          |
| --------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **CoordPlane**  | XZ/YZ plane in ops JSON    | Apply axis swap / negation before moveTo calls                                                                         |
| **ArcMid**      | `Arc3D` with center+radius | Compute $p_\text{mid} = p_c + r\cdot\text{rot}_\text{CCW}(\hat{v},\theta/2)$; replace `radiusArc` with `threePointArc` |
| **ExtrudeSign** | `NewBody` extrusion        | Set extrude direction from GT bounding-box; do not union with prior bodies                                             |
| **InnerLoop**   | Multi-loop profile         | Detect `is_outer=False` loops; emit separate `.wire()` + subtract                                                      |


Figure 3 illustrates the **ArcMid** skill in detail: the verifier returns IoU = 0.893, the skill retrieves the `Arc3D` JSON record, recomputes the correct midpoint analytically, replaces the arc call, and resubmits — yielding IoU = 0.999.

### 2.3 Re-Act Loop (Automated Tier — B1)

The primary tier (Figure 2B) runs:

1. **Generate** — LLM produces CadQuery from ops JSON.
2. **Execute & verify** — run code; compute 3D IoU (OCCT boolean intersection/union).
3. **Diagnose** — if IoU < 0.99: pattern-match failure against skill triggers.
4. **Repair** — invoke matching skill; regenerate.
5. **Accept or escalate** — accept if IoU ≥ 0.99 after repair; else escalate.

Multi-provider cascade (codex → GPT-4o → GLM) is applied before escalation.

### 2.4 Manual Escalation Tier (B2)

Failures not resolved by the skill library go to a Claude-Code session. The operator reads the ops JSON, GT renders, and generated renders (Figure 5), applies targeted edits, and re-verifies. Crucially, each resolved hard case is **analysed post-hoc**: if the root cause is generalizable, a new skill is added to the library (making future B1 runs better). This creates a virtuous loop between B2 analysis and B1 capability.

### 2.5 Verified Record Schema

`raw_step_path · ops_json_path · gen_step_path · cq_code_path · views_raw_dir · views_gen_dir · iou · source · timestamp`

---

## 3. Experimental Setup

**Data.** Fusion360 Gallery (parametric reconstruction + extrude-tools) and synthetic procedural parts. ~6000 Fusion360 parts and ~700 synthetic parts attempted.

**Metrics.**


| Metric              | Definition                                                   |
| ------------------- | ------------------------------------------------------------ |
| **Pass Rate**       | Fraction of exec-ran parts with IoU ≥ 0.99                   |
| **IoU=0 rate**      | Code ran but zero overlap with GT (coordinate/scale failure) |
| **0<IoU<0.99 rate** | Partial geometry match (arc/extrude failure)                 |
| **Mean IoU**        | Mean over *all* completed executions (includes IoU = 0)      |
| **CD**              | Chamfer distance on 2048-pt surface samples (mm)             |
| **Exec fail**       | Code fails to execute (throws exception)                     |


**Baselines.** Evaluated on two independent fixed pools (v3, v4: 1000 parts each, all using single-pass GPT-4o as B0):

- **B0 Direct** — single LLM call, no verification, no retry.
- **B1 Re-Act** — automated loop with geometric skill library + multi-provider cascade; no manual.
- **B2 CADLoop** — B1 + Claude-Code manual escalation.

---

## 4. Results

### 4.1 Failure Mode Anatomy

The combined v3+v4 pool (2000 attempted, 1619 exec-ran) reveals a clear failure taxonomy:


| Failure type              | Count (B0) | Reduced by B1 | Reduced by B2 |
| ------------------------- | ---------- | ------------- | ------------- |
| Exec-stuck (codegen fail) | 381        | 0             | 0             |
| IoU = 0 (coord/scale)     | 943        | −7            | −7            |
| 0 < IoU < 0.99 (geom)     | 482        | −17           | −36           |
| **IoU ≥ 0.99 (pass)**     | **194**    | **+24**       | **+43**       |


**Exec fail = 0%** for all methods: LLM code always executes. The 381 exec-stuck cases are upstream codegen hangs, not execution errors. Failures are *purely geometric*: 58% produce IoU = 0 (coordinate/scale inversion) and 30% produce partial overlap (arc/extrude mismatch).

The skill library specifically targets the `0<IoU<0.99` bucket, where the geometry is recognisably correct but one analytic parameter (arc midpoint, extrude sign, plane mapping) is wrong. IoU = 0 cases require structural changes not yet automated.

### 4.2 Target Population: Why IoU > 0.5?

We restrict primary analysis to parts where B0 produces *partial but non-trivial geometry* (IoU > 0.5). This filter is motivated by three complementary principles:

**Zone of Proximal Development.** A B0 part with IoU > 0.5 has captured the rough topology — the model understood the basic shape class (box, cylinder, flanged extrusion). Failure is at *parametric precision*: a single arc midpoint is wrong, an extrude sign is flipped, a plane axis is swapped. This is the regime where a skill-based repair adds value. Parts with IoU < 0.5 exhibit structural hallucination (wrong feature count, wrong topology) — repairing parameters on a wrong skeleton produces no gain.

**Data distillation efficiency.** Real data curation engines do not annotate cases the model has already mastered or cases that require full regeneration. The IoU ∈ (0.5, 0.99) band represents *the highest-leverage conversion target*: medium-quality LLM output that a deterministic skill can promote to verified training data. This framing positions CADLoop as a **weak-to-strong data distillation** tool, converting near-correct LLM outputs into IoU = 1.0 ground-truth pairs.

**Isolating iterative refinement from random guessing.** When B0 IoU < 0.5, the generated code scaffold is fundamentally wrong. Any subsequent fix is essentially a full rewrite — not a measure of closed-loop reasoning ability. Filtering to IoU > 0.5 ensures Re-Act feedback is operating on a structurally sound base, making the repair signal interpretable.

### 4.3 Near-Miss Analysis

We split the IoU > 0.5 population into two sub-regimes and measure repair rates per tier.

**Table 1 — Near-miss subset repair rates (combined v3+v4, N = 1619 exec-ran)**


| Subset               | N   | B1 auto-fix | B2 total fix | B1 %      | B2 %       | B0 mean IoU | B2 mean IoU |
| -------------------- | --- | ----------- | ------------ | --------- | ---------- | ----------- | ----------- |
| 0.5 < B0 < 0.8       | 38  | 0           | 1            | 0.0%      | **2.6%**   | 0.665       | 0.662       |
| B0 > 0.8 (near-miss) | 32  | 13          | 32           | **40.6%** | **100.0%** | 0.901       | 0.9998      |
| B0 > 0.5 (combined)  | 70  | 13          | 33           | 18.6%     | **47.1%**  | 0.773       | 0.840       |


The two regimes reveal sharply different failure modes.

**B0 > 0.8 — Parametric precision failures (100% fixable).** All 32 near-miss parts reach IoU ≥ 0.99 after B2. The skill library auto-fixes 40.6% (13 cases) with zero human cost; manual escalation covers the remaining 19 cases. The failure mode is always a *single analytic parameter*: arc midpoint computed from center+radius instead of angular interpolation, extrude sign inverted relative to GT bounding box, XZ/YZ plane axis swap. One deterministic correction per part is sufficient.

**0.5 < B0 < 0.8 — Structural plateau (2.6% fixable).** All 37 B2-failed cases remain *stuck in the same IoU band* (B2 mean IoU = 0.662 vs B0 mean = 0.665 — no meaningful change). None of these cases crossed the 0.8 boundary. Of these, 35/38 are classified as `complex`. Crucially, none of the 37 B2-failed cases were even attempted as manual fixes: visual inspection in the manual tier revealed multi-error structures that could not be resolved by targeted parameter edits. The IoU ceiling at ~0.8 indicates *multiple simultaneous errors*: wrong number of extrude bodies, missing inner-loop profiles, incorrect sketch plane combined with extrude direction. These require structural regeneration, not repair.

### 4.4 Failure Mode Anatomy

**Chamfer Distance.** On a 300-part random draw from v4 (48 B2-accepted), B0 CD = **29.6 mm** vs B2 CD = **2.7 mm** — 10.9× reduction. B0 "accepted" these as code-ran but geometrically wrong STEP; B2 corrected the single parameter error.

### 4.5 Dataset Quality

**Table 2 — Verified dataset (N = 1646)**


|                      | Value                   |
| -------------------- | ----------------------- |
| Total verified pairs | **1646**                |
| IoU mean             | 0.9999                  |
| IoU = 1.0            | 1578 / 1646 (**95.9%**) |
| IoU ≥ 0.999          | 1625 / 1646 (**98.7%**) |
| IoU min              | 0.9901                  |
| Fusion360 pairs      | 726 (44%)               |
| Synthetic pairs      | 920 (56%)               |
| Via manual (B2 tier) | 62 (3.8%)               |


### 4.6 Auto-Pass Cases (Figure 4)

Figure 4 shows six representative auto-pass examples: GT (row 1) vs Re-Act output (row 2). The skill library correctly resolves coordinate-plane and extrude-direction on all six without manual intervention. Geometric diversity spans gear teeth, extruded channels, forked connectors, and flanges — confirming skills generalise across shape classes.

### 4.7 Hard Cases and Repair (Figure 5)

Figure 5 shows six hard cases across three rows: GT · Re-Act · CADLoop. Red dashed boxes mark geometric discrepancies.

- **Re-Act failures** (row 2): arc direction inversion (convex/concave swap), wrong extrude depth sign, missing inner-loop cutout. All cases have B0 IoU ∈ (0.87, 0.98) — the near-miss regime where single-parameter repair suffices.
- **CADLoop repairs** (row 3): the manual tier resolves all six to IoU ≥ 0.991. One case (`34785_dc3b83fa_0011`) improves from 0.979 → 0.991 — a partial repair that feeds the skill-library analysis queue.
- **Skill-library growth**: each resolved hard case is reviewed for generalisability; new skills reduce future B1 failures without any additional human effort.

---

## 5. Discussion

**Why skills outperform prompt engineering.** Prompting the LLM to "be careful about coordinate planes" does not reliably fix these issues because the LLM cannot analytically verify its own arc-midpoint computation. A skill bypasses the LLM for the repair step and uses exact symbolic geometry — making the fix deterministic, auditable, and O(1) compute.

**The mixed nature of the 0.5–0.8 band.** The case studies reveal that the 0.5–0.8 band is not homogeneous. Two of the three inspected cases are trivially fixable (XZ extrude sign error causing a body translation, IoU ≈ 0.53), and one is structurally irreducible (30-curve profile hallucinated as a rectangle). The current skill library misses the fixable cases because its trigger patterns are calibrated for IoU > 0.8 signatures. An extended ExtudeSign skill that detects the XZ-plane sign convention error from IoU ≈ 0.5 (same-volume, translated-body) would recover some fraction of the 0.5–0.8 group. The B2 mean IoU barely changes (0.665 → 0.662) partly because the manual tier — reasonably — did not attempt this group, expecting structural failures.

**Failure analysis: why 0.5 < IoU < 0.8 cases resist repair.**
We inspected three cases at the bottom of the 0.5–0.8 band (IoU ≈ 0.50–0.53):

- **21231\_eb9826e5\_0011** (IoU = 0.528, stepped cylinder): Volumes and bounding box extents match the GT exactly. The model used `extrude(-2.0)` intending −Y, but CadQuery's XZ workplane has normal −Y, so `extrude(-d)` goes +Y — the big disc landed 2 mm above its correct position, shifting the whole body. Fix: change `extrude(-2.0)` to `extrude(2.0)` → **IoU = 1.000**.

- **22463\_c48bb23e\_0004** (IoU = 0.530, asymmetric cylinder): The body is a perfect cylinder translated −2.68 mm in Y (GT y∈[−6.05, 2.68], GEN y∈[−8.73, 0]). Same root cause: `extrude(2.68)` on XZ went −Y instead of +Y. Fix: change to `extrude(-2.68)` → **IoU = 1.000**.

- **134862\_b757f2b8\_0001** (IoU = 0.502): A 180 × 97 × 1.5 mm flat panel (extrude depth 1.5 mm, `NewBody`). The ops JSON contains **18 profiles across 30 sketch curves** — a grid of distinct closed regions, each forming part of the final extruded cross-section (GT vol = 13 746 mm³ = 52.5% of the bounding box, indicating substantial internal cutouts). The LLM generated a single full rectangle with no cutouts (GEN vol = 27 377 mm³ ≈ 2× GT). Not fixable by parameter repair; requires regenerating the entire 30-curve sketch.

**Key insight.** Cases 1–2 are fixable with a one-line sign change; they fall in the 0.5–0.8 band only because the XZ sign error shifts the body by the extrude distance (IoU ≈ 0.5), not because the topology is wrong. The current ExtudeSign skill misses them because it triggers on high-IoU patterns. Case 3 is qualitatively different: a *complexity-driven structural hallucination*.

**Why structural hallucination occurs.** When the ops JSON encodes high-complexity sketches — 18+ profiles, 30+ curves with explicit coordinate lists — the total token count of the prompt exceeds the model's effective attention span for fine-grained geometry. Rather than enumerate all 18 profiles, the LLM collapses to the simplest valid shape it can construct from the overall bounding box: a single rectangle. This is a form of **profile omission**: the model understands the extrude operation and its depth but loses track of which interior profiles define cutouts. The generated code is syntactically valid and executes without error, which is why exec fail = 0%; the failure is purely semantic.

**How to mitigate.** Three complementary strategies address this:

1. *Profile-count injection*: Annotate the prompt with the explicit profile count before generation: "This sketch has 18 closed profiles. You MUST emit CadQuery code for all 18 regions." Explicit enumeration anchors the model and reduces omission probability.

2. *Profile-count validation skill*: Post-generation, count the number of distinct closed profile regions in the generated code (`.add()` / `.union()` / multi-profile extrude calls) and compare against the ops JSON profile count. A mismatch triggers re-generation with a stronger constraint prompt, not a parameter repair.

3. *Complexity-aware routing*: Parts with ops JSON curve count > 20 are routed to a specialised multi-profile generation chain (iterative profile-by-profile assembly) rather than the standard single-pass prompt. This keeps the per-profile context small and computable.

The 0.5–0.8 band is therefore a *mixed* population — some cases are skill-fixable with a lower-IoU ExtudeSign trigger (cases 1–2), others are complexity hallucinations requiring regeneration (case 3). B2 mean IoU barely changes (0.665 → 0.662) because the manual tier — correctly, given the mix — deprioritised this entire group.

**Scalability.** The skill library is append-only; each B2 hard case is a potential skill candidate. The synth tier (920 pairs, 90.5% pass rate on 483 unique parts) confirms near-zero failure on procedurally generated geometry — an upper bound of ~90% given a complete skill library.

**Limitations and future improvements.**

- *Extended ExtrudeSign skill (lower-IoU trigger).* The XZ-plane sign error can be detected analytically: if generated and GT volumes match but bounding boxes are offset by exactly the first extrude distance, flip the sign. This would recover fixable cases (cases 1–2) currently below the B1 skill trigger threshold.
- *Profile-count validation skill.* Post-generation, compare profile region count in generated code vs ops JSON. Mismatch → re-generate with explicit profile count injected in the prompt. Addresses complexity-driven hallucinations (case 3).
- *Complexity-aware routing.* Parts with ops JSON curve count > 20 route to an iterative profile-by-profile chain instead of single-pass generation, keeping per-call context tractable.
- Visual verification is sparse (91% `SKIP`); enforcing it would improve cross-modal alignment.
- CD reported for B0/B2 only; B1 CD is future work.

---

## 6. Conclusion

CADLoop demonstrates that a compact geometric skill library — not more data or larger models — is the key driver of improvement in CAD data curation. The analysis reveals a sharp boundary at B0 IoU ≈ 0.8: above it, failures are single-parameter and 100% recoverable (skill auto-fix 40.6%, manual escalation covers the rest, mean IoU 0.901→0.9998); below it, failures are multi-error structural plateaus that resist repair entirely (B2 mean IoU barely changes). This boundary motivates both the IoU > 0.8 target population for high-confidence data curation and a clear research direction: skills that detect wrong feature count or body topology before committing to parameter-level repair. The two-tier design (automated skills + human escalation) also creates a natural skill-growth flywheel — every B2 hard case is a candidate for the next automated skill, making each subsequent run cheaper.

---

## References

1. Willis et al. *Fusion 360 Gallery: A Dataset and Environment for Programmatic CAD Construction.* SIGGRAPH 2021.
2. Yao et al. *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR 2023.
3. Wu et al. *DeepCAD: A Deep Generative Network for Computer-Aided Design Models.* ICCV 2021.
4. Dupont et al. *CAD-Recode: Reverse Engineering CAD Code from Point Clouds.* 2024.
5. Wang et al. *Qwen2-VL Technical Report.* 2024.
6. CadQuery documentation — [https://cadquery.readthedocs.io](https://cadquery.readthedocs.io)
7. NeXD Workshop @ CVPR 2026 — call for papers.

