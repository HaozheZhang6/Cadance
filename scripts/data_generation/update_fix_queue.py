#!/usr/bin/env python3
"""Update fix_queue.csv status after fixing a near-miss.

Usage:
  python scripts/data_generation/update_fix_queue.py <stem> --status done --fixed-iou 1.0 --note "threePointArc fix"
  python scripts/data_generation/update_fix_queue.py <stem> --status failed --note "complex spline, skip"
"""

import argparse
import csv
import datetime
import sys
from pathlib import Path

QUEUE = Path("data/data_generation/fix_queue.csv")

try:
    import db as _db
except ImportError:
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).parent))
    import db as _db


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stem")
    p.add_argument(
        "--status",
        choices=["pending", "in_progress", "done", "failed", "skipped"],
        required=True,
    )
    p.add_argument("--fixed-iou", type=float, default=None)
    p.add_argument("--note", default="")
    args = p.parse_args()

    rows = []
    found = False
    with open(QUEUE) as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["stem"] == args.stem:
                row["status"] = args.status
                row["attempts"] = str(int(row.get("attempts") or 0) + 1)
                if args.fixed_iou is not None:
                    row["fixed_iou"] = str(round(args.fixed_iou, 6))
                if args.note:
                    row["fix_note"] = args.note
                row["updated_at"] = datetime.datetime.utcnow().strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                found = True
            rows.append(row)

    if not found:
        print(
            f"WARNING: stem '{args.stem}' not found in fix_queue.csv", file=sys.stderr
        )
        sys.exit(1)

    with open(QUEUE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Updated {args.stem} → status={args.status}"
        + (f" iou={args.fixed_iou}" if args.fixed_iou else "")
    )

    # sync parts.csv and operations.csv
    db_status = "verified" if args.status == "done" else "failed"
    run = next((r.get("run", "") for r in rows if r["stem"] == args.stem), "")
    _db.update_part_status(
        stem=args.stem,
        status=db_status,
        iou=args.fixed_iou,
        fix_note=args.note or None,
    )
    _db.log_operation(
        stem=args.stem,
        run=run,
        op_type="manual_fix",
        provider="claude",
        result=db_status,
        iou=args.fixed_iou,
    )


if __name__ == "__main__":
    main()
