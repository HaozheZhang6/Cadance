#!/usr/bin/env python3
"""Generate all sample figures + companion metadata for BenchCAD.

Each figure → paper/references/bench-data/sample_figs/<name>.png
Each metadata → paper/references/bench-data/sample_figs/<name>.md

Usage:
  uv run python3 -m scripts.bench_data.viz.run_all
"""

from __future__ import annotations

from pathlib import Path

from scripts.bench_data.viz import figures as F

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "paper/references/bench-data/sample_figs"
OUT.mkdir(parents=True, exist_ok=True)


# Each entry: (name, generator, reference papers, role in source, our impl, storyline contribution)
FIGS = [
    ("01_family_distribution",
     F.fig_family_distribution,
     ["text2cad", "objaverse_xl", "infinity_chat"],
     "data-stats: prove dataset breadth in one bar.",
     "synth_parts.csv → groupby(family).size, top-40 colored by macro bucket.",
     "Defends 'BenchCAD covers 106 families' against the sketch-extrude monoculture critique. "
     "Drops into §4 Dataset / Coverage."),

    ("02_difficulty_heatmap",
     F.fig_difficulty_heatmap,
     ["sportu", "text2cad", "bbeh"],
     "per-difficulty / per-skill breakdown — defeat aggregate-collapse.",
     "synth_parts.csv → pivot family×difficulty, top-25 families.",
     "Shows BenchCAD has real per-family difficulty stratification, supporting "
     "decision #6 (per-column reporting + hard-column collapse punchline)."),

    ("03_status_breakdown",
     F.fig_status_breakdown,
     ["mmlu_pro", "mmsi_bench", "webarena_verified"],
     "construction-quality transparency — count rejections, list reasons.",
     "synth_parts.csv → status pie + reject_reason top-8 horizontal bars.",
     "Reviewer-pleaser: shows we throw away bad data rather than ship it. "
     "Mirrors mmlu_pro Table 1 issue counts (350 incorrect / 1953 false-neg / 862 bad-format)."),

    ("04_macro_taxonomy",
     F.fig_macro_taxonomy,
     ["gmai_mmbench", "agentbench", "infinity_chat"],
     "taxonomy / skill-tree — memorable structure imposed before numbers.",
     "synth_parts.csv → 2-ring polar (inner=6 macros, outer=families).",
     "The headline taxonomy figure (decision #3). 6 buckets ≤ memory ceiling, "
     "full 106 leaves available as appendix filter (gmai_mmbench-style queryable tree)."),

    ("05_iso_pareto",
     F.fig_iso_pareto,
     ["gmai_mmbench", "olympiadbench"],
     "coverage claim — top-N standards + cumulative %.",
     "synth_parts.csv → standard.value_counts top-15 + cumulative line.",
     "Shows ISO/DIN compliance breadth. Anchors our 'industrial-grade' positioning "
     "vs DeepCAD's 'random parametric'."),

    ("06_scaling_cliff",
     F.fig_scaling_cliff,
     ["text2cadquery", "mmsi_bench", "objaverse_xl"],
     "scaling curve / ablation — non-saturation or scaling cliff.",
     "MOCK: hard-coded Qwen 0.5/1.5/3/7/14/32/72B vs IoU pass; pending real eval.",
     "Decision #16 — one-figure-headline if scaling fails to lift CAD accuracy. "
     "Contrast text2cadquery's clean scaling with our (predicted) cliff."),

    ("07_mini_full_correlation",
     F.fig_mini_full_correlation,
     ["webarena_verified", "convcodeworld", "bigcodebench"],
     "correlation scatter — justify a cheap proxy via rank fidelity.",
     "MOCK: 30 simulated models (rng=42), Spearman computed.",
     "Decision #5 — Mini (1.4k) vs Full (17.8k) rank preservation. "
     "Without this, reviewers can't trust the cheap version we ship for fast iteration."),

    ("08_preflight_funnel",
     F.fig_preflight_funnel,
     ["mmlu_pro", "cadevolve", "gpqa"],
     "construction pipeline — 4-stage funnel with survivor counts.",
     "Hard-coded counts reflecting the CLAUDE.md pre-flight rule "
     "(124 → register → build-test → geom-valid → solid → vis-text → 106).",
     "Decision #11 — visualises the engineering investment that produced 106 working families. "
     "Cheap reviewer credibility win."),

    ("09_error_taxonomy",
     F.fig_error_taxonomy,
     ["mmsi_bench", "mathvista", "sportr"],
     "failure case grid — named categories with explicit % mass.",
     "MOCK: 5-category taxonomy (wrong-primitive / topology / dimension / constraint / axis); "
     "real percentages pending model eval.",
     "Decision #13 — converts qualitative model failure into citable category mass. "
     "Gives every follow-up paper an attack vector to claim improvement on."),

    ("10_hero_composite",
     F.fig_hero_composite,
     ["mmsi_bench", "mmlu_pro", "text2cad"],
     "hero panel — 4-panel composite (taxonomy + difficulty + scaling + headline gap).",
     "Combines real synth_parts.csv stats (panels a, b) with mock numbers (c, d).",
     "Decision #1 — the cover-page figure for BenchCAD. Sells four sub-claims at once: "
     "(a) 6-macro structure, (b) real difficulty stratification, (c) scaling cliff, "
     "(d) human–model gap with separate hard-column bar."),

    ("11_op_coverage_gallery",
     F.fig_op_coverage_gallery,
     ["cadevolve", "objaverse_xl", "blenderllm_cadbench"],
     "qualitative side-by-side — visual proof bench is what it claims.",
     "Samples 9 PNGs from data/data_generation/iso_106_codegen/png/ with diverse stems.",
     "Visual evidence that we cover op-diversity beyond sketch+extrude. "
     "Pairs with the gap-table to refute reviewer monoculture worries."),

    ("12_modality_ablation",
     F.fig_modality_ablation,
     ["spatialeval", "mmmu_pro", "convcodeworld"],
     "modality / input-format ablation — same item, three formats.",
     "MOCK: 5 frontier models × 3 input modes (image / json / both); pending real eval.",
     "Decision #15 — proves the visual axis isn't theatrical. spatialeval-style 3-format "
     "ablation is the cleanest defense against 'multimodal-in-name-only' critique."),

    ("13_gap_vs_prior",
     F.fig_gap_table,
     ["gmai_mmbench", "mmiu", "olympiadbench"],
     "gap-vs-prior table — kill all related work in one ✓/✗ grid.",
     "Hard-coded comparison vs DeepCAD / Text2CAD / CAD-Recode / CADPrompt / "
     "BlenderLLM-CADBench / Text-to-CadQuery / HistCAD on 6 axes.",
     "Decision #12 — politely demolishes prior CAD benches. The single-table version of "
     "the related-work section."),

    ("14_construction_pipeline",
     F.fig_construction_pipeline,
     ["autocodebench", "mmlu_pro", "cap3d"],
     "construction pipeline — methodology cookbook readers will copy.",
     "5-stage box-and-arrow diagram (registry → build → IoU verify → render → 5-task pairs).",
     "Decision #14 — §3 anchor figure. Reviewers love being able to re-implement from "
     "the figure alone."),

    ("15_difficulty_per_macro",
     F.fig_difficulty_per_macro,
     ["bbeh", "spider2", "text2cad"],
     "per-skill breakdown — stacked easy/medium/hard per macro.",
     "synth_parts.csv → pivot macro×difficulty, stacked bar.",
     "Per-macro stacking exposes whether our difficulty mix is uniform or skewed. "
     "Supports the per-column reporting move (decision #6)."),
]


def main() -> int:
    metas = []
    for name, gen, refs, role, impl, storyline in FIGS:
        png = OUT / f"{name}.png"
        md = OUT / f"{name}.md"
        try:
            gen(png)
            ok = True
            err = None
        except Exception as e:
            ok = False
            err = repr(e)
        ref_links = ", ".join(f"`{r}`" for r in refs)
        md_text = f"""# {name}

**Reference papers:** {ref_links}
**Role in source:** {role}
**Our implementation:** {impl}
**Storyline contribution:** {storyline}
{"" if ok else f"**ERROR:** {err}"}
"""
        md.write_text(md_text)
        metas.append((name, ok, err))
        status = "OK" if ok else f"FAIL: {err[:80]}"
        print(f"{name}: {status}")
    n_ok = sum(1 for _, ok, _ in metas if ok)
    print(f"\n{n_ok}/{len(metas)} figures generated → {OUT}")
    return 0 if n_ok == len(metas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
