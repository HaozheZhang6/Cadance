# Digest Agent Prompt Template (per category)

Insert {{CATEGORY_LETTER}} (A–G), {{CATEGORY_NAME}}, {{PAPER_LIST}} (slug + title + venue lines).

---

You are writing benchmark-paper digests for a NeurIPS 2026 D&B submission called BenchCAD (a CAD code-generation benchmark).

Your category: **{{CATEGORY_LETTER}}. {{CATEGORY_NAME}}**

Papers ({{N}} total):
{{PAPER_LIST}}

For each paper above, write `paper/references/bench-data/<slug>/digest.md`:

```markdown
# <slug> — <full title>

**Venue:** <venue> · **Year:** <year> · **URL:** <url> · **PDF:** raw.pdf

## TL;DR
<one sentence: who built what bench, scale, headline finding>

## Storyline (5-piece)
- **Problem.** What gap in the field? What did prior bench fail at?
- **Contribution.** Bench size / structure / annotation / new task. Specific numbers.
- **Evidence (approach).** How they constructed it — pipeline, annotators, validation, dedup.
- **Experiments.** Models tested, metric definitions, headline numbers.
- **Analysis.** What surprised them. Failure modes. Where models still fall short.

## Figures (role in story)
Read `pages/page-NN.png` (1-12). Pick **3–5** figures/tables that carry the story. For each:
1. Copy the source PNG to `figs/fig01_<role>.png` … `figs/fig05_<role>.png` (use `cp pages/page-XX.png figs/figNN_role.png`).
2. Fill the table:

| # | Page | Type (figure/table) | Role | Description (≤20 words) | What they show |
|---|------|---------------------|------|-------------------------|----------------|
| 1 | 1 | figure | hero | … | … |
| 2 | 3 | table | gap-vs-prior | … | … |
| 3 | 5 | figure | taxonomy | … | … |

Roles to choose from (pick whatever fits): `hero`, `gap-vs-prior`, `taxonomy`, `pipeline`, `data-stats`, `headline-results`, `failure-cases`, `ablation`, `case-study`, `radar-comparison`, `correlation`, `human-vs-model`.

## Takeaways for BenchCAD
3–5 bullets. Be specific about what we can borrow / contrast / avoid for our paper. Reference our existing assets when relevant (cad_iso_106 / cad_simple_ops_100k / 41 family / 17.8k bench rows).

## One-line citation
Bib-style: `Authors et al. (Year). Title. Venue.` from page 1.
```

Constraints:
- Ground every claim in the actual PDF. If a number isn't in the paper, say so.
- For [have] papers (text2cad, cad_coder, cad_recode, cadrille, cadevolve, cadcodeverify, autocodebench, infinity_chat, mmsi_bench, sportr, sportu) — read the existing `paper/references/notes/<slug>.md` (they're 30–80 lines each), then expand into the new schema. Don't lose insights from the notes.
- Tables: 1 row per figure picked. Skip if a paper has fewer than 3 figures worth showing — just put what's there and note it.
- Never invent a figure number you didn't actually copy. CHECKED: figs/ directory has the file you reference.
- Prefer pages 1–6 (teaser, intro figs, taxonomy diagrams), but go further if a key results figure lives on page 8–10.
- Output ONLY: per-paper `digest.md` files + per-paper `figs/*.png` copies. No other writes.

When done, report: `<N>/<N> done; figures copied: <total>; any failures: <slug list>`. Under 150 words.
