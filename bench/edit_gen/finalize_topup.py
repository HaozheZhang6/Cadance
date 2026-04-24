"""Merge Phase-2 (non-boss) + Phase-3b records into final curated output.

- Drop all add_boss records
- Auto-tag difficulty by op_name
- Write merged records.jsonl, manifest.csv (with num + difficulty)
- Copy orig/gt step files to a unified directory
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
P2 = BENCH / "topup_diverse"
P3B = BENCH / "topup_phase3b"
OUT = BENCH / "topup_final"

# op_name → difficulty
EASY_OPS = {
    "outer_fillet", "outer_chamfer",
    "top_circle_fillet", "top_circle_chamfer",
    "bottom_circle_fillet", "bottom_circle_chamfer",
    "axial_hole",
}
MEDIUM_OPS = {
    "radial_hole", "radial_hole_X", "radial_hole_Y",
    "offset_axial_hole", "top_slot", "hex_socket",
    "all_circle_chamfer",
}


def derive_difficulty(op_name: str) -> str:
    if op_name in EASY_OPS:
        return "easy"
    if op_name in MEDIUM_OPS:
        return "medium"
    return "medium"  # fallback


def main():
    # Load P2 non-boss
    p2 = [
        json.loads(ln) for ln in
        (P2 / "records.jsonl").read_text().splitlines() if ln
    ]
    p2_clean = [r for r in p2 if r["edit_type"] != "add_boss"]

    # Load P3b
    p3b_path = P3B / "records.jsonl"
    p3b = []
    if p3b_path.exists():
        p3b = [json.loads(ln) for ln in p3b_path.read_text().splitlines() if ln]

    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    merged: list[dict] = []
    for src_dir, recs in [(P2, p2_clean), (P3B, p3b)]:
        for r in recs:
            rid = r["record_id"]
            # Copy 4 files per record
            for sub, ext in [("codes", ".py"), ("steps", ".step")]:
                for kind in ["orig", "gt"]:
                    src = src_dir / sub / f"{rid}_{kind}{ext}"
                    dst = (codes_dir if sub == "codes" else steps_dir) / \
                        f"{rid}_{kind}{ext}"
                    if src.exists() and not dst.exists():
                        shutil.copy(src, dst)
            op_name = rid.split("_", 2)[-1] if rid.startswith("topup_p3b_") \
                else "_".join(rid.split("_")[2:])
            # Derive op_name more robustly: it's everything after family name
            # rid formats:
            #   topup_<family>_<op_name>
            #   topup_p3b_<family>_<op_name>
            parts = rid.split("_")
            if parts[1] == "p3b":
                fam_start = 2
            else:
                fam_start = 1
            # Find op_name by matching family
            fam = r["family"]
            # Rebuild op_name from rid tail
            prefix = f"topup_p3b_{fam}_" if parts[1] == "p3b" \
                else f"topup_{fam}_"
            op_name = rid[len(prefix):] if rid.startswith(prefix) else "unknown"

            diff = derive_difficulty(op_name)
            merged.append({
                **r,
                "difficulty": diff,
                "op_name": op_name,
                "orig_code_path": f"codes/{rid}_orig.py",
                "gt_code_path": f"codes/{rid}_gt.py",
                "orig_step_path": f"steps/{rid}_orig.step",
                "gt_step_path": f"steps/{rid}_gt.step",
            })

    # Sort: family asc, difficulty (easy before medium)
    diff_rank = {"easy": 0, "medium": 1, "hard": 2}
    merged.sort(key=lambda r: (r["family"], diff_rank.get(r["difficulty"], 9)))

    # Write jsonl
    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in merged)
    )

    # Per-family coverage report
    by_fam: dict = {}
    for r in merged:
        by_fam.setdefault(r["family"], []).append(
            {"type": r["edit_type"], "op": r["op_name"],
             "diff": r["difficulty"], "iou": r.get("iou")}
        )
    report = {
        "total_records": len(merged),
        "families_total": len(by_fam),
        "families_ge2": sum(1 for f, rs in by_fam.items() if len(rs) >= 2),
        "families_1": sum(1 for f, rs in by_fam.items() if len(rs) == 1),
        "by_family": by_fam,
    }
    (OUT / "coverage_report.json").write_text(json.dumps(report, indent=2))

    # CSV
    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "num", "record_id", "family", "edit_type", "difficulty",
            "iou", "instruction"
        ])
        for idx, r in enumerate(merged, 1):
            w.writerow([
                idx, r["record_id"], r["family"], r["edit_type"],
                r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float) else "",
                r["instruction"],
            ])

    # Per-family summary table (for the "easy vs medium" description)
    summary_path = OUT / "per_family_summary.md"
    lines = ["| family | easy edit | medium edit |",
             "|---|---|---|"]
    for fam in sorted(by_fam.keys()):
        rs = by_fam[fam]
        easy = next((r for r in rs if r["diff"] == "easy"), None)
        medium = next((r for r in rs if r["diff"] == "medium"), None)
        e_str = f"{easy['type']}/{easy['op']}" if easy else "—"
        m_str = f"{medium['type']}/{medium['op']}" if medium else "—"
        lines.append(f"| {fam} | {e_str} | {m_str} |")
    summary_path.write_text("\n".join(lines))

    print(f"merged: {len(merged)} records, {len(by_fam)} families")
    print(f"  ≥2 ops: {report['families_ge2']}, 1 op: {report['families_1']}")
    # Missing families
    from bench.edit_gen.edit_axes import EDIT_AXES
    missing = set(EDIT_AXES.keys()) - set(by_fam.keys())
    print(f"  missing: {len(missing)} -> {sorted(missing)[:20]}")
    print(f"wrote {OUT}/ (records.jsonl, manifest.csv, "
          f"coverage_report.json, per_family_summary.md)")


if __name__ == "__main__":
    main()
