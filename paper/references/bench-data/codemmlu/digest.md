# codemmlu — CodeMMLU: A Multi-Task Benchmark for Assessing Code Understanding & Reasoning Capabilities of Code LLMs

**Venue:** ICLR 2025 (OpenReview) · **Year:** 2024 · **URL:** https://github.com/FSoft-AI4Code/CodeMMLU · **PDF:** raw.pdf

## TL;DR
~20K MMLU-style multiple-choice questions across 50+ SE topics and 10+ languages, separating code *understanding* from *generation* and exposing that even DeepSeek-R1 struggles.

## Storyline (5-piece)
- **Problem.** Code benchmarks are dominated by open-ended generation; LLMs may pass via memorization. There is no MMLU-style understanding benchmark for SE that can scale and resist contamination.
- **Contribution.** CodeMMLU: ~20K MCQs across code analysis, defect detection, fill-in-blank, completion, repair, execution prediction, DBMS/SQL, frameworks, software-engineering principles in 10+ languages.
- **Evidence (approach).** Curate from textbooks + StackOverflow + LeetCode-discussion + open exams; permute answer-choice order to mitigate position bias; precision-only metric (no judge model).
- **Experiments.** Evaluate 30+ LLMs (proprietary GPT-4o / Claude / o3-mini, open DeepSeek/Llama/Qwen-Coder/Phi); per-task radar; CoT vs. direct prompting; HumanEval reframed as MCQ.
- **Analysis.** (1) GPT-4o / Claude lead; (2) DeepSeek family best open; (3) within-family scaling holds, across-family doesn't; (4) CoT *hurts* CodeMMLU performance for many models; (5) reframing HumanEval as MCQ drops scores — generation may rely on memorization.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 2 | radar chart | hero | Per-task accuracy of 7 frontier models on 10 CodeMMLU axes | Pattern of strengths/weaknesses across understanding sub-tasks |
| 2 | 4 | task taxonomy | taxonomy | Tree of 50+ SE topics grouped into syntax / repair / completion / DBMS / etc. | Coverage breadth |
| 3 | 7 | results table | headline-results | Accuracy of 30+ LLMs on full CodeMMLU and subsets | GPT-4o / Claude top; open-source gap |
| 4 | 9 | scatter | correlation | CodeMMLU vs. HumanEval per model + CoT effect | Understanding ≠ generation; CoT often harmful |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** Pair generation tasks with comprehension MCQs over the *same* parts. We should add a CAD-MCQ track — "which dimension is the through-hole diameter?" / "which feature was removed?" — to detect models that draw correct CAD without grasping it.
- **Borrow:** Permute answer choices to break MCQ position bias; we should randomize sketch / view order in any multi-choice CAD QA.
- **Borrow:** Quantify the gap between generation and understanding. Their HumanEval-MCQ reframing is clever; we can reframe BenchCAD-Gen items as multiple-choice "which CadQuery snippet matches" to test memorization.
- **Contrast:** Multiple-choice can be brittle (Robinson 2023 etc.); for CAD where ground truth is a 3D shape, exec-IoU is stronger. Use MCQ as a *complement*, not the headline metric.
- **Avoid:** Replacing exec-grading with MCQ. CodeMMLU's own analysis shows MCQ scores ≠ generation skill — keep IoU front and center.

## One-line citation
CodeMMLU [Nguyen-Manh et al., ICLR 2025] introduces a 20K-question MMLU-style benchmark across 50+ SE topics that decouples code understanding from generation, revealing that even DeepSeek-R1 lags behind GPT-4o and that CoT prompting often *hurts* code reasoning.
