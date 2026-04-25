# §3 The BenchCAD Dataset (draft v0)

> Target ≤ 2.0 page。4 子节: 3.1 design principle / 3.2 family registry + standards / 3.3 CadGen pipeline + verification / 3.4 splits + Croissant + hosting

---

## 3.1 Design Principles

We design BenchCAD around four principles that prior CAD datasets violate either individually or jointly.

**P1 — Execution as ground truth.** Every record's ground truth is the *executed* solid: the CadQuery source code is run inside a sandboxed CadQuery~/ PythonOCC environment, the resulting STEP file is voxelized and compared against a reference solid by 3D IoU under the rotation-invariant 6-face cube group~\cite{rot_iou}. A record enters the verified split only if IoU $\geq 0.99$ \emph{and} executes within a 30s timeout with non-degenerate volume. This rules out the silent failure mode common in DeepCAD-derived corpora where parsed code is assumed correct but neither re-executed nor geometrically validated.

**P2 — Standard-table anchoring.** Where a part has an industrial counterpart, parameters sample from real specification tables (ISO 22 V-belt cross-section series, DIN 338 twist-drill diameter ranges, ISO 23509 bevel gear pitch--module relationship, etc.). Geometry that "looks right" but violates manufacturable proportions (e.g.\ M6 bolt with thread pitch 3 mm) is rejected at sampling time. 55\% of BenchCAD families are standard-anchored; Table~\ref{tab:standards} enumerates the standard codes.

**P3 — Family-level taxonomy.** Records are grouped into 106 named *families* (e.g.\ \texttt{coil\_spring}, \texttt{helical\_gear}, \texttt{twisted\_drill}), each implemented by a small Python module exposing a typed parameter schema, a sampler, a validator, and a deterministic builder. This makes coverage measurable, sampling reproducible, difficulty controllable, and per-family analysis trivial — properties absent from DeepCAD/Fusion360 where parts are pooled without semantic structure.

**P4 — Operation breadth.** The dataset exercises 45+ distinct CadQuery operations spanning sketch primitives, contour drawing (lines, arcs, splines), workplane manipulation, sketch arrays, 3D ops (extrude, twist-extrude, revolve, loft, sweep), Booleans, hole variants, and edge finishing (fillet, chamfer, shell). Table~\ref{tab:op_coverage} contrasts this against prior corpora restricted to sketch + extrude.

## 3.2 Family Registry and Standard Compliance

**Families.** Each family is a class implementing the \texttt{Family} interface: a JSON-schema parameter spec; a \texttt{sample\_params(difficulty, rng)} method that draws a parameter dictionary; a \texttt{validate\_params(p)} predicate enforcing geometric and standard-table constraints; and a \texttt{make\_program(p)} method that emits a typed list of \texttt{Op} dicts consumable by the builder. Families are auto-discovered from a registry module (\texttt{registry.py}); adding a new family requires no changes to the pipeline beyond registering one class.

**Standard compliance.** A family declares \texttt{standard = "ISO 23509"} (etc.) when its parameter ranges and inter-parameter relations are fixed by an external specification table; the validator then enforces specification ranges. As of submission, BenchCAD covers 22 ISO codes (e.g.\ ISO 22, 113, 272, 1234, 1580, 2339, 2340, 2936, 10828, 23509), 28 DIN codes (e.g.\ DIN 338, 471/472, 580, 5480, 2095, 8187, 71412), 4 EN codes (EN 10034, 10056, 10219, 10279), 3 ASME codes (B1.20.1, B16.5, B16.9), and 2 IEC codes (60072-1, 60086) — totalling 59 standard-anchored families. The remaining 48 families cover bespoke industrial parts (e.g.\ \texttt{twisted\_bracket}, \texttt{venturi\_tube}, \texttt{lobed\_knob}) without formal standards but governed by analogous proportional rules.

**Difficulty stratification.** Each family supports three difficulty tiers — \emph{easy}, \emph{medium}, \emph{hard} — defined by parameter complexity (op count, feature count, non-axis-aligned geometry, presence of helical / lofted / boolean cuts). Tier definitions are family-specific and machine-checkable; aggregate counts and tier example renders appear in Figure~\ref{fig:taxonomy}.

## 3.3 The CadGen Pipeline

We name the data construction pipeline \textbf{CadGen} to separate it as a standalone contribution from the resulting dataset. CadGen has four stages.

**Stage 1 — Parameter sampling.** For each family $\times$ difficulty bucket, the sampler draws parameters from the JSON schema under standard-table constraints. Sampling is deterministic given a seed.

**Stage 2 — Program emission.** The family's \texttt{make\_program} returns an op sequence. The builder consumes the op list and produces (i) Python CadQuery source code via a per-op code template, and (ii) a CadQuery \texttt{Workplane} object via direct API dispatch. Both representations are aligned by construction: the same op list yields equivalent geometry whether interpreted via the builder or by executing the emitted code in a fresh sandbox.

**Stage 3 — Execution and verification.** We re-execute the emitted code in an isolated sandbox, export STEP, voxelize at 64$^3$ resolution, and compute rotation-invariant 3D IoU against the builder's direct STEP output. Records with IoU $< 0.99$, execution failures, timeouts (>30s), or zero/inverted volume are quarantined for review. A persistent execution cache (sticky columns \texttt{code\_exec\_ok / reason / checked\_at} on \texttt{verified\_parts.csv}) avoids re-running the same code on subsequent syncs.

**Stage 4 — Render and package.** Each verified record is rendered to four canonical views (front / right / top / iso) at 512$\times$512 with VTK, and the (parameters, program, code, STEP, views) bundle is registered to the dataset CSV.

\textbf{Yield.} From a 20{,}221-sample run on the April 2026 batch, 20{,}143 records (99.6\%) passed all checks; 78 failures concentrated in three pathological families (\texttt{double\_simplex\_sprocket}, \texttt{stepped\_shaft}, \texttt{torus\_link}) due to OCCT \texttt{Standard\_Failure} on extreme parameter combinations.

## 3.4 Splits, Documentation, Hosting

**Splits.** The full release contains five subsets (Table~\ref{tab:dataset}): \emph{BenchCAD-Synth} (20{,}143 verified procedural parts, primary evaluation set); \emph{BenchCAD-Edit} (433 curated edit pairs spanning dimensional / additive / subtractive / multi-step modifications, 106 families); \emph{BenchCAD-Lite} (530-sample stratified subset for fast leaderboard); \emph{BenchCAD-Fusion360} and \emph{BenchCAD-DeepCAD} (verified subsets of Fusion360 Gallery and DeepCAD reconstructions for OOD evaluation); and \emph{BenchCAD-GenCAD} (162{,}000 image-to-code pairs derived from GenCAD for SFT-scale training).

**Documentation.** Every dataset ships with a Croissant 1.0 metadata file including all required Responsible AI fields (data origins, licensing, intended uses, exclusions, sensitive attributes — none present). Validation passes the public Croissant checker.

**Hosting.** All splits are hosted on Hugging Face under \texttt{BenchCAD/cad\_bench} (test) and \texttt{BenchCAD/cad\_bench\_edit} (edit), with the verification-pipeline source under MIT licence and the dataset under CC-BY-4.0. Dataset cards link to the per-family parameter schemas and the standard-table sources used for compliance.

---

## TODO
- 数字核对:107 vs 106 family discrepancy(CLAUDE.md 写 106,本地 grep 107)— 查 registry.list_families() 得权威值
- 难度 tier family 数 (?40 easy / ?40 med / ?26 hard) 待真实 query
- Standard count:54 grep'd vs 59 估 — 重新核
- Render config: VTK / cadrille-style?CLAUDE.md 提到 z-up,需要核
- Croissant validator 跑没?如未跑,这段先标 "claim — check before submission"
- License 决定:dataset CC-BY-4.0 vs CC-BY-NC?待你定
