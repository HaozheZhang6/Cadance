"""Publication-quality distribution figures for bench_subset_1200.

Outputs (PDF + PNG @ 300 DPI):
  fig1_overview.{pdf,png}        — 2x2 main panel: family/difficulty/ops/complexity
  fig2_family_bar.{pdf,png}      — full 106-family bar chart by tier
  fig3_op_coverage.{pdf,png}     — op coverage horizontal bar (log x-axis)
  fig4_family_op_heatmap.{pdf,png} — family × op heatmap (top families × ops)
  fig5_complexity.{pdf,png}      — bbox + n_ops violin by difficulty

Style: NeurIPS D&B-friendly. Sans-serif, restrained palette, no chartjunk.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SUBSET_JSON = ROOT / "data" / "data_generation" / "bench_subset_1200.json"
OUT_DIR = ROOT / "data" / "data_generation" / "bench_subset_figs"


# Tier sets — kept in sync with select_bench_subset.py
HEAVY = {
    "spur_gear", "helical_gear", "bevel_gear", "sprocket",
    "double_simplex_sprocket", "worm_screw", "impeller", "propeller",
    "coil_spring", "torsion_spring", "bellows",
}
LIGHT = {
    "spacer_ring", "circlip", "dowel_pin", "taper_pin", "cotter_pin",
    "parallel_key", "rivet", "grommet", "washer",
}

TIER_COLORS = {"HEAVY": "#d62728", "STANDARD": "#1f77b4", "LIGHT": "#2ca02c"}
DIFF_COLORS = {"easy": "#7fcdbb", "medium": "#41b6c4", "hard": "#225ea8"}


def tier_of(fam: str) -> str:
    if fam in HEAVY:
        return "HEAVY"
    if fam in LIGHT:
        return "LIGHT"
    return "STANDARD"


def setup_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "legend.frameon": False,
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })


def save_fig(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        path = OUT_DIR / f"{name}.{ext}"
        fig.savefig(path)
        print(f"  → {path}")


PLANE_COLORS = {"XY": "#4c72b0", "YZ": "#dd8452", "XZ": "#55a868"}


def fig1_overview(subset, ds_rows):
    """2×3 main panel: family / difficulty / plane / top ops / n_ops / plane×diff."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 9))
    fig.suptitle(f"BenchCAD-{len(ds_rows)} benchmark subset — distribution overview",
                 fontsize=14, fontweight="bold", y=0.995)

    # ── (a) Top 20 families
    ax = axes[0, 0]
    fc = Counter(r["family"] for r in ds_rows)
    top = fc.most_common(20)
    fams = [f for f, _ in top]
    counts = [c for _, c in top]
    colors = [TIER_COLORS[tier_of(f)] for f in fams]
    ax.barh(range(len(fams)), counts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(fams)))
    ax.set_yticklabels(fams, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("# samples")
    ax.set_title("(a) Top-20 families (color = tier)")
    # Legend
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in TIER_COLORS.values()]
    ax.legend(handles, TIER_COLORS.keys(), loc="lower right", fontsize=8)

    # ── (b) Difficulty donut
    ax = axes[0, 1]
    dc = Counter(r["difficulty"] for r in ds_rows)
    labels = ["easy", "medium", "hard"]
    sizes = [dc.get(k, 0) for k in labels]
    colors = [DIFF_COLORS[k] for k in labels]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 2},
        textprops={"fontsize": 10},
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title(f"(b) Difficulty distribution\n(N = {sum(sizes)})")

    # ── (c) base_plane donut
    ax = axes[0, 2]
    pc = Counter(r.get("base_plane", "XY") for r in ds_rows)
    plane_labels = ["XY", "YZ", "XZ"]
    plane_sizes = [pc.get(p, 0) for p in plane_labels]
    plane_colors = [PLANE_COLORS[p] for p in plane_labels]
    wedges_c, texts_c, autotexts_c = ax.pie(
        plane_sizes, labels=plane_labels, colors=plane_colors, autopct="%1.1f%%",
        startangle=90, wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 2},
        textprops={"fontsize": 10},
    )
    for t in autotexts_c:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title(f"(c) base_plane distribution\n(N = {sum(plane_sizes)})")

    # ── (d) Top 15 ops
    ax = axes[1, 0]
    op_counter = Counter()
    for r in ds_rows:
        for op in json.loads(r.get("ops_used", "[]") or "[]"):
            op_counter[op] += 1
    top_ops = op_counter.most_common(15)
    ops = [o for o, _ in top_ops]
    cnts = [c for _, c in top_ops]
    ax.barh(range(len(ops)), cnts, color="#5c8bb5", edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(ops)))
    ax.set_yticklabels(ops, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("op occurrences")
    ax.set_title(f"(d) Top-15 ops ({len(op_counter)} unique total)")

    # ── (e) n_ops by difficulty (violin)
    ax = axes[1, 1]
    n_by_diff = defaultdict(list)
    for r in ds_rows:
        diff = r.get("difficulty", "?")
        n = len(json.loads(r.get("ops_used", "[]") or "[]"))
        n_by_diff[diff].append(n)
    parts = ax.violinplot(
        [n_by_diff[d] for d in labels],
        positions=range(3),
        showmeans=True, widths=0.7,
    )
    for body, k in zip(parts["bodies"], labels):
        body.set_facecolor(DIFF_COLORS[k])
        body.set_edgecolor("white")
        body.set_alpha(0.85)
    parts["cmeans"].set_color("black")
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels)
    ax.set_ylabel("# ops per sample")
    ax.set_title("(e) n_ops by difficulty")

    # ── (f) plane × difficulty stacked bar
    ax = axes[1, 2]
    pd_counts: dict[tuple, int] = Counter()
    for r in ds_rows:
        pd_counts[(r.get("base_plane", "XY"), r.get("difficulty", "?"))] += 1
    bottoms = np.zeros(3)
    for d in labels:
        h = np.array([pd_counts.get((p, d), 0) for p in plane_labels])
        ax.bar(plane_labels, h, bottom=bottoms, color=DIFF_COLORS[d],
               edgecolor="white", linewidth=0.5, label=d, width=0.65)
        bottoms += h
    ax.set_ylabel("# samples")
    ax.set_title("(f) plane × difficulty stacked")
    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    save_fig(fig, "fig1_overview")
    plt.close(fig)


def fig2_family_bar(subset, ds_rows):
    """All 106 families, sorted by count, color by tier."""
    fc = Counter(r["family"] for r in ds_rows)
    items = sorted(fc.items(), key=lambda x: (-x[1], x[0]))
    fams = [f for f, _ in items]
    counts = [c for _, c in items]
    colors = [TIER_COLORS[tier_of(f)] for f in fams]

    fig, ax = plt.subplots(figsize=(15, 16))
    ax.barh(range(len(fams)), counts, color=colors, edgecolor="white", linewidth=0.4)
    ax.set_yticks(range(len(fams)))
    ax.set_yticklabels(fams, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("# samples")
    ax.set_title(f"BenchCAD subset — all {len(fams)} families × tier ({sum(counts)} samples)",
                 fontsize=12, fontweight="bold")

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in TIER_COLORS.values()]
    ax.legend(handles, TIER_COLORS.keys(), loc="lower right", fontsize=10, title="Tier")
    plt.tight_layout()
    save_fig(fig, "fig2_family_bar")
    plt.close(fig)


def fig3_op_coverage(subset, ds_rows):
    """All ops, log x-axis, color by abundance tier."""
    op_counter = Counter()
    for r in ds_rows:
        for op in json.loads(r.get("ops_used", "[]") or "[]"):
            op_counter[op] += 1
    items = sorted(op_counter.items(), key=lambda x: x[1])
    ops = [o for o, _ in items]
    cnts = [c for _, c in items]
    colors = ["#d62728" if c < 30 else ("#ff7f0e" if c < 100 else "#5c8bb5") for c in cnts]

    fig, ax = plt.subplots(figsize=(11, 10))
    ax.barh(range(len(ops)), cnts, color=colors, edgecolor="white", linewidth=0.4)
    ax.set_yticks(range(len(ops)))
    ax.set_yticklabels(ops, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("op occurrences (log scale)")
    ax.set_title(f"BenchCAD subset — op vocabulary coverage ({len(ops)} unique ops)",
                 fontsize=12, fontweight="bold")
    ax.axvline(30, color="#d62728", linestyle="--", linewidth=0.7, alpha=0.7,
               label="rare-op threshold (30)")
    ax.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    save_fig(fig, "fig3_op_coverage")
    plt.close(fig)


def fig4_family_op_heatmap(subset, ds_rows):
    """Family (rows) × op (cols) co-occurrence heatmap, log scale."""
    fc = Counter(r["family"] for r in ds_rows)
    op_counter = Counter()
    for r in ds_rows:
        for op in json.loads(r.get("ops_used", "[]") or "[]"):
            op_counter[op] += 1

    # Top 40 families, top 25 ops by total occurrences.
    top_fams = [f for f, _ in fc.most_common(40)]
    top_ops = [o for o, _ in op_counter.most_common(25)]
    M = np.zeros((len(top_fams), len(top_ops)), dtype=int)
    for r in ds_rows:
        f = r["family"]
        if f not in top_fams:
            continue
        i = top_fams.index(f)
        for op in json.loads(r.get("ops_used", "[]") or "[]"):
            if op in top_ops:
                M[i, top_ops.index(op)] += 1

    fig, ax = plt.subplots(figsize=(14, 11))
    M_log = np.log1p(M)
    im = ax.imshow(M_log, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(top_ops)))
    ax.set_xticklabels(top_ops, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(top_fams)))
    ax.set_yticklabels(top_fams, fontsize=7)
    ax.set_title("Family × op co-occurrence (top 40 fam × top 25 op, log color)",
                 fontsize=12, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, label="log1p(occurrences)", shrink=0.8)
    plt.tight_layout()
    save_fig(fig, "fig4_family_op_heatmap")
    plt.close(fig)


def fig5_complexity(subset, ds_rows):
    """n_ops violin by difficulty + feature_count by tier + n_ops histogram."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    diffs = ["easy", "medium", "hard"]

    # n_ops by diff
    ax = axes[0]
    n_by_diff = defaultdict(list)
    for r in ds_rows:
        n = len(json.loads(r.get("ops_used", "[]") or "[]"))
        n_by_diff[r["difficulty"]].append(n)
    parts = ax.violinplot(
        [n_by_diff[d] for d in diffs],
        positions=range(3),
        showmeans=True, widths=0.7,
    )
    for body, k in zip(parts["bodies"], diffs):
        body.set_facecolor(DIFF_COLORS[k])
        body.set_edgecolor("white")
        body.set_alpha(0.85)
    parts["cmeans"].set_color("black")
    ax.set_xticks(range(3))
    ax.set_xticklabels(diffs)
    ax.set_ylabel("# ops per sample")
    ax.set_title("(a) n_ops by difficulty")

    # feature_count by tier
    ax = axes[1]
    fc_by_tier = defaultdict(list)
    for r in ds_rows:
        fc_by_tier[tier_of(r["family"])].append(int(r.get("feature_count", 0) or 0))
    tiers = ["LIGHT", "STANDARD", "HEAVY"]
    parts = ax.violinplot(
        [fc_by_tier[t] for t in tiers],
        positions=range(3),
        showmeans=True, widths=0.7,
    )
    for body, t in zip(parts["bodies"], tiers):
        body.set_facecolor(TIER_COLORS[t])
        body.set_edgecolor("white")
        body.set_alpha(0.8)
    parts["cmeans"].set_color("black")
    ax.set_xticks(range(3))
    ax.set_xticklabels(tiers)
    ax.set_ylabel("feature_count")
    ax.set_title("(b) feature_count by family tier")

    # n_ops overall histogram with diff stack
    ax = axes[2]
    bins = range(0, max(len(json.loads(r.get("ops_used", "[]") or "[]"))
                         for r in ds_rows) + 2)
    bottoms = np.zeros(len(bins) - 1, dtype=float)
    for d in diffs:
        n_list = n_by_diff[d]
        h, _ = np.histogram(n_list, bins=bins)
        ax.bar(bins[:-1], h, bottom=bottoms, color=DIFF_COLORS[d],
               edgecolor="white", linewidth=0.4, label=d, width=1.0, align="edge")
        bottoms += h
    ax.set_xlabel("# ops per sample")
    ax.set_ylabel("# samples")
    ax.set_title(f"(c) n_ops distribution stacked by diff (N={len(ds_rows)})")
    ax.legend(loc="upper right", fontsize=9)

    plt.suptitle("BenchCAD subset — geometric complexity",
                 fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    save_fig(fig, "fig5_complexity")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", default=str(SUBSET_JSON))
    args = ap.parse_args()

    setup_style()
    subset = json.loads(Path(args.subset).read_text())
    stem_set = set(subset["stems"])
    print(f"Loaded subset: {len(stem_set)} stems")

    print("Loading BenchCAD/cad_bench (filtering to subset) ...")
    from datasets import load_dataset
    ds = load_dataset("BenchCAD/cad_bench", split="test")
    ds_rows = [r for r in ds if r["stem"] in stem_set]
    print(f"  filtered to {len(ds_rows)} rows")

    print("\nfig1: overview ...")
    fig1_overview(subset, ds_rows)
    print("\nfig2: family bar ...")
    fig2_family_bar(subset, ds_rows)
    print("\nfig3: op coverage ...")
    fig3_op_coverage(subset, ds_rows)
    print("\nfig4: family × op heatmap ...")
    fig4_family_op_heatmap(subset, ds_rows)
    print("\nfig5: complexity ...")
    fig5_complexity(subset, ds_rows)

    print(f"\n✓ Figures saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
