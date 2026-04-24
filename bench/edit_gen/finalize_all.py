"""Combine all topup rounds into topup_final/.

Sources:
  - topup_diverse/records.jsonl (drop add_boss)
  - topup_manual/records.jsonl (only status=ok)
  - topup_rotate/records.jsonl (all)

Output:
  - topup_final/records.jsonl
  - topup_final/manifest.csv (num, record_id, family, edit_type, difficulty, iou, instruction)
  - topup_final/per_family_summary.md
  - topup_final/coverage_report.json
  - copies codes/*.py and steps/*.step into topup_final/
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "data" / "data_generation" / "bench_edit"
P2 = BENCH / "topup_diverse"
MANUAL = BENCH / "topup_manual"
ROTATE = BENCH / "topup_rotate"
OUT = BENCH / "topup_final"


def derive_difficulty(rid: str, edit_type: str) -> str:
    """Heuristic difficulty from op_name in record_id."""
    if edit_type == "rotate":
        return "easy"
    # Check op keywords
    rid_l = rid.lower()
    if any(k in rid_l for k in ["outer_fillet", "outer_chamfer",
                                 "corner_fillet", "top_chamfer",
                                 "top_circle", "bottom_circle",
                                 "rim_chamfer", "rim_fillet",
                                 "end_chamfer", "bore_widen", "widen_bore",
                                 "axial_hole"]):
        return "easy"
    return "medium"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    codes_dir = OUT / "codes"
    steps_dir = OUT / "steps"
    codes_dir.mkdir(exist_ok=True)
    steps_dir.mkdir(exist_ok=True)

    REMOVE = BENCH / "topup_remove"
    DIM = BENCH / "topup_dim"
    merged: list[dict] = []
    # For families that now have dim edits, drop their rotate_Y90 (keep X only)
    dim_fams = set()
    dim_jl = DIM / "records.jsonl"
    if dim_jl.exists():
        for ln in dim_jl.read_text().splitlines():
            if ln:
                dim_fams.add(json.loads(ln)["family"])
    sources = [
        (P2, "p2", lambda r: r["edit_type"] != "add_boss"),
        (MANUAL, "manual", lambda r: r.get("status") == "ok"),
        (ROTATE, "rotate",
         lambda r: not (r["family"] in dim_fams
                         and r["record_id"].endswith("_Y90"))),
        (REMOVE, "remove",
         lambda r: r.get("status") == "ok"
                   or (r.get("iou") is not None and r["iou"] < 0.99)),
        (DIM, "dim", lambda r: r.get("status") == "ok"),
    ]
    for src_dir, tag, filt in sources:
        rec_file = src_dir / "records.jsonl"
        if not rec_file.exists():
            print(f"skip {src_dir}: no records.jsonl")
            continue
        recs = [json.loads(ln) for ln in rec_file.read_text().splitlines() if ln]
        kept = [r for r in recs if filt(r)]
        for r in kept:
            rid = r["record_id"]
            # Copy code + step files
            for sub, ext in [("codes", ".py"), ("steps", ".step")]:
                for kind in ["orig", "gt"]:
                    src = src_dir / sub / f"{rid}_{kind}{ext}"
                    dst = (codes_dir if sub == "codes" else steps_dir) / \
                        f"{rid}_{kind}{ext}"
                    if src.exists() and not dst.exists():
                        shutil.copy(src, dst)
            diff = r.get("difficulty") or derive_difficulty(rid, r["edit_type"])
            merged.append({
                "record_id": rid,
                "family": r["family"],
                "edit_type": r["edit_type"],
                "difficulty": diff,
                "instruction": r["instruction"],
                "iou": r.get("iou"),
                "source": tag,
                "orig_code_path": f"codes/{rid}_orig.py",
                "gt_code_path": f"codes/{rid}_gt.py",
                "orig_step_path": f"steps/{rid}_orig.step",
                "gt_step_path": f"steps/{rid}_gt.step",
            })
        print(f"  {tag}: +{len(kept)} records")

    # Sort by family, difficulty
    diff_rank = {"easy": 0, "medium": 1, "hard": 2}
    merged.sort(key=lambda r: (r["family"], diff_rank.get(r["difficulty"], 9),
                                r["edit_type"]))

    # Write jsonl
    (OUT / "records.jsonl").write_text(
        "\n".join(json.dumps(r) for r in merged)
    )

    # CSV
    csv_path = OUT / "manifest.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["num", "record_id", "family", "edit_type", "difficulty",
                    "iou", "source", "instruction", "orig_code", "gt_code"])
        for idx, r in enumerate(merged, 1):
            orig_py = OUT / r["orig_code_path"]
            gt_py = OUT / r["gt_code_path"]
            orig_code = orig_py.read_text() if orig_py.exists() else ""
            gt_code = gt_py.read_text() if gt_py.exists() else ""
            w.writerow([
                idx, r["record_id"], r["family"], r["edit_type"],
                r["difficulty"],
                f"{r.get('iou'):.4f}" if isinstance(r.get("iou"), float) else "",
                r["source"], r["instruction"], orig_code, gt_code,
            ])
    print(f"wrote {csv_path}")

    # Per-family coverage
    by_fam: dict = {}
    for r in merged:
        by_fam.setdefault(r["family"], []).append(r)
    from bench.edit_gen.edit_axes import EDIT_AXES
    all_fams = set(EDIT_AXES.keys())
    cov = {
        "total_records": len(merged),
        "families_with_records": len(by_fam),
        "families_ge2": sum(1 for f, rs in by_fam.items() if len(rs) >= 2),
        "families_1": sum(1 for f, rs in by_fam.items() if len(rs) == 1),
        "families_0": len(all_fams - set(by_fam.keys())),
        "missing_families": sorted(all_fams - set(by_fam.keys())),
    }
    type_counts = {}
    for r in merged:
        type_counts[r["edit_type"]] = type_counts.get(r["edit_type"], 0) + 1
    cov["type_distribution"] = type_counts
    (OUT / "coverage_report.json").write_text(json.dumps(cov, indent=2))

    # Per-family summary markdown
    lines = ["| family | easy | medium |",
             "|---|---|---|"]
    for fam in sorted(by_fam.keys()):
        rs = by_fam[fam]
        easy = [r for r in rs if r["difficulty"] == "easy"]
        medium = [r for r in rs if r["difficulty"] == "medium"]
        e_str = ", ".join(r["edit_type"].replace("add_", "") for r in easy) or "—"
        m_str = ", ".join(r["edit_type"].replace("add_", "") for r in medium) or "—"
        lines.append(f"| {fam} | {e_str} | {m_str} |")
    # Append missing
    for fam in sorted(all_fams - set(by_fam.keys())):
        lines.append(f"| {fam} | **MISSING** | **MISSING** |")
    (OUT / "per_family_summary.md").write_text("\n".join(lines))

    print(f"\n=== Final coverage ===")
    print(f"total records: {cov['total_records']}")
    print(f"families with ≥2: {cov['families_ge2']}/106")
    print(f"families with =1: {cov['families_1']}")
    print(f"families with =0: {cov['families_0']} -> {cov['missing_families']}")
    print(f"type distribution: {type_counts}")


if __name__ == "__main__":
    main()
