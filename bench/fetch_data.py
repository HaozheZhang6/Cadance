"""一键预拉 bench 数据到 HF cache + 解包 edit bench 给 UI 用。

跑任何 runner 前 `uv run python bench/fetch_data.py` 一次,
之后 eval / qa / edit 全部走 ~/.cache/huggingface,无网延迟。

附带:把 cad_bench_edit 解包到 `data/data_generation/bench_edit/from_hf/`,
对齐 UI (`scripts/data_generation/ui/app.py` 编辑 Bench 页) 期望的本地路径
schema (records.jsonl + orig_steps/ + gt_steps/ + orig_codes/ + gt_codes/),
fresh clone 起 streamlit 后立即可视.

默认两个 repo:
  - BenchCAD/cad_bench       (img2cq + qa)
  - BenchCAD/cad_bench_edit  (edit, 自动解包到 from_hf/)

Usage:
    python bench/fetch_data.py
    python bench/fetch_data.py --repo Hula0401/cad_external_bench
    python bench/fetch_data.py --no-ui-dump        # 只填 HF cache, 不解包
    python bench/fetch_data.py --force-ui-dump     # 强制覆盖 from_hf/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

from bench.dataloader import load_hf  # noqa: E402

DEFAULT_REPOS = [
    "BenchCAD/cad_bench",
    "BenchCAD/cad_bench_edit",
]

EDIT_REPO = "BenchCAD/cad_bench_edit"
UI_DUMP_DIR = ROOT / "data" / "data_generation" / "bench_edit" / "from_hf"

UI_META_KEYS = (
    "record_id",
    "family",
    "edit_type",
    "difficulty",
    "instruction",
    "iou",
    "source",
)


def fetch_one(repo: str, split: str, token: str | None) -> list[dict]:
    print(f"[fetch] {repo}:{split} ...", flush=True)
    rows = load_hf(repo, split, token=token)
    print(f"[fetch] {repo}:{split} -> {len(rows)} rows OK", flush=True)
    return rows


def _write_bytes(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, dict) and "bytes" in data:
        data = data["bytes"]
    if isinstance(data, str):
        data = data.encode("utf-8")
    p.write_bytes(data)


def _write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text or "")


def dump_edit_for_ui(rows: list[dict], out_dir: Path, force: bool = False) -> int:
    """把 cad_bench_edit HF rows 解包成 UI 期望的本地 schema.

    UI 读 `<base_dir>/records.jsonl`,每条 record 引用相对路径
    `orig_step_path` / `gt_step_path` / `gt_code_path` / `orig_code_path`.
    """
    records_path = out_dir / "records.jsonl"
    if records_path.exists() and not force:
        try:
            existing = sum(1 for _ in records_path.open())
        except Exception:
            existing = 0
        if existing == len(rows):
            print(
                f"[ui-dump] {records_path.relative_to(ROOT)} 已存在 ({existing} 行) — skip",
                flush=True,
            )
            return existing

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[ui-dump] -> {out_dir.relative_to(ROOT)} ({len(rows)} rows)", flush=True)

    n = 0
    with records_path.open("w") as f:
        for row in rows:
            rid = row.get("record_id")
            if not rid:
                continue
            orig_step = row.get("orig_step")
            gt_step = row.get("gt_step")
            orig_code = row.get("orig_code") or ""
            gt_code = row.get("gt_code") or ""
            if not (orig_step and gt_step and gt_code):
                continue

            orig_step_rel = f"orig_steps/{rid}.step"
            gt_step_rel = f"gt_steps/{rid}.step"
            orig_code_rel = f"orig_codes/{rid}.py"
            gt_code_rel = f"gt_codes/{rid}.py"

            _write_bytes(out_dir / orig_step_rel, orig_step)
            _write_bytes(out_dir / gt_step_rel, gt_step)
            _write_text(out_dir / orig_code_rel, orig_code)
            _write_text(out_dir / gt_code_rel, gt_code)

            rec = {k: row.get(k) for k in UI_META_KEYS if row.get(k) is not None}
            rec["record_id"] = rid
            rec["orig_step_path"] = orig_step_rel
            rec["gt_step_path"] = gt_step_rel
            rec["orig_code_path"] = orig_code_rel
            rec["gt_code_path"] = gt_code_rel
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1

    print(f"[ui-dump] wrote {n} records + {n*2} STEP + {n*2} code files", flush=True)
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--repo",
        action="append",
        default=None,
        help="HF repo id; 可重复; 缺省 = 两个 BenchCAD repo",
    )
    ap.add_argument("--split", default="test")
    ap.add_argument(
        "--no-ui-dump",
        action="store_true",
        help="只填 HF cache,不解包 edit bench 到本地 (UI 编辑 Bench 页将无法直读)",
    )
    ap.add_argument(
        "--force-ui-dump",
        action="store_true",
        help="即便 from_hf/records.jsonl 已存在也重新解包",
    )
    args = ap.parse_args()

    token = os.environ.get("BenchCAD_HF_TOKEN") or os.environ.get("HF_TOKEN")
    repos = args.repo if args.repo else DEFAULT_REPOS

    failed: list[tuple[str, str]] = []
    edit_rows: list[dict] | None = None
    for repo in repos:
        try:
            rows = fetch_one(repo, args.split, token)
            if repo == EDIT_REPO:
                edit_rows = rows
        except Exception as e:
            print(f"[fetch] {repo}:{args.split} FAIL: {e}", file=sys.stderr, flush=True)
            failed.append((repo, str(e)))

    if edit_rows is not None and not args.no_ui_dump:
        try:
            dump_edit_for_ui(edit_rows, UI_DUMP_DIR, force=args.force_ui_dump)
        except Exception as e:
            print(f"[ui-dump] FAIL: {e}", file=sys.stderr, flush=True)
            failed.append(("ui-dump", str(e)))

    if failed:
        print(f"[fetch] {len(failed)} 步失败", file=sys.stderr)
        return 1
    msg = f"[fetch] done -- {len(repos)} repo cached"
    if edit_rows is not None and not args.no_ui_dump:
        msg += f"; UI 编辑 Bench 走 {UI_DUMP_DIR.relative_to(ROOT)} (数据源: from_hf)"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
