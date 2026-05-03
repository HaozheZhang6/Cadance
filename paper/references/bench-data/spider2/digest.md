# spider2 — Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows

**Venue:** ICLR 2025 (Oral) · **Year:** 2024 · **URL:** https://spider2-sql.github.io · **PDF:** raw.pdf

## TL;DR
632 enterprise-grade text-to-SQL workflow tasks over BigQuery / Snowflake / DuckDB databases averaging 812 columns; best agent (o1-preview) reaches only 21.3% vs. 91.2% on Spider 1.0 — text-to-SQL is far from solved.

## Storyline (5-piece)
- **Problem.** Spider 1.0 / BIRD use small synthetic schemas and one SQL dialect; real enterprise workflows mean 1k+ column schemas, dialect docs, codebase context, multi-step transformations, and 100+ line queries.
- **Contribution.** Spider 2.0 (632 agentic workflow tasks across cloud + local DBs) plus Spider 2.0-Lite and Spider 2.0-Snow (self-contained text-to-SQL slices); evaluation framework with project codebase + DB interface.
- **Evidence (approach).** Sourced from Salesforce / Google Analytics / dbt-style projects; agent must navigate code, docs, dialect refs, then emit multiple SQL queries; full execution-based grading on real DBs.
- **Experiments.** Code-agent built on o1-preview / GPT-4o / Claude vs. dedicated text-to-SQL parsers; report execution accuracy on Spider 2.0, 2.0-Lite, 2.0-Snow; per-dialect breakdowns.
- **Analysis.** Best agent 21.3%; best text-to-SQL parser only 5.7% on Lite. Failure clusters: schema linking on huge schemas, dialect-specific functions, multi-query planning, codebase comprehension.

## Figures (role in story)
| # | Page | Type | Role | Description (≤20 words) | What they show |
|---|------|------|------|-------------------------|----------------|
| 1 | 1 | task overview | hero | Enterprise question + multi-table schema + 100-line SQL with codebase | Real-world workflow task structure |
| 2 | 4 | dataset construction | pipeline | Source selection → schema/doc collection → human authoring → exec verification | How Spider 2.0 tasks are built |
| 3 | 5 | comparison stats | data-stats | Spider 2.0 vs. Spider 1.0 / BIRD: schema size, SQL length, dialects | 812 cols vs. ~30; 144 SQL tokens vs. 21 |
| 4 | 7 | exec-accuracy table | headline-results | Performance of agent + parser baselines on three subsets | o1-preview agent 21.3%; parser 5.7% on Lite |

## Takeaways for BenchCAD (CAD-code-gen NeurIPS 2026 D&B benchmark)
- **Borrow:** "Lite + full agentic" split. Spider 2.0 ships a text-to-SQL-only Lite for easy comparison with prior parsers + a full agent setting for realism. Mirror with BenchCAD-static (single-shot CadQuery) vs. BenchCAD-agent (CAD repair / multi-turn / kernel feedback).
- **Borrow:** Surface contextual complexity (schema size, dialect docs, codebase) as first-class metrics. For CAD: number of dimensions, number of constraints, number of references — quantify the task difficulty axis explicitly.
- **Borrow:** Evaluation by *execution* on real engines (BigQuery / Snowflake) vs. string match. We already use CadQuery execution + IoU; argue this aligns with their ICLR-Oral methodology.
- **Contrast:** Their bottleneck is schema-linking on huge metadata; ours is part-of-feature localization in a 3D scene. Both are "find-relevant-context" problems — useful framing.
- **Avoid:** Single-number reporting. Their three subsets (full / Lite / Snow) let readers separate agent capability from text-to-SQL capability; we should also separate single-shot codegen from multi-turn / agentic results.

## One-line citation
Spider 2.0 [Lei et al., ICLR 2025 Oral] introduces 632 enterprise text-to-SQL workflow tasks over 800-column real schemas where the best o1-preview agent reaches only 21.3% accuracy, demonstrating that long-context, multi-dialect, codebase-grounded SQL remains an open problem.
