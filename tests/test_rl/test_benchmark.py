"""Tests for scripts/rl/benchmark.py."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.rl.benchmark import _eval_one, _load_samples, _summarise


def _make_row(i: int, hundred: bool = True) -> dict:
    return {
        "id": f"test_{i:04d}",
        "hundred_subset": hundred,
        "messages": [
            {"role": "system", "content": "You are a CadQuery expert."},
            {"role": "user", "content": "Generate code"},
            {"role": "assistant", "content": f"import cadquery as cq\nresult = cq.Workplane().box({i},{i},{i})\nresult.val().exportStep('output.step')"},
        ],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


class TestLoadSamples:
    def test_hundred_subset_filter(self, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        rows = [_make_row(i, hundred=(i < 3)) for i in range(5)]
        _write_jsonl(jsonl, rows)
        samples = _load_samples(jsonl, hundred_subset=True, n=0, seed=42)
        assert len(samples) == 3
        assert all(s["hundred_subset"] for s in samples)

    def test_seed_sample(self, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        rows = [_make_row(i, hundred=False) for i in range(20)]
        _write_jsonl(jsonl, rows)
        s1 = _load_samples(jsonl, hundred_subset=False, n=5, seed=42)
        s2 = _load_samples(jsonl, hundred_subset=False, n=5, seed=42)
        assert [r["id"] for r in s1] == [r["id"] for r in s2]
        assert len(s1) == 5

    def test_n_limits_hundred_subset(self, tmp_path):
        jsonl = tmp_path / "data.jsonl"
        rows = [_make_row(i, hundred=True) for i in range(10)]
        _write_jsonl(jsonl, rows)
        samples = _load_samples(jsonl, hundred_subset=True, n=3, seed=42)
        assert len(samples) == 3


class TestEvalOne:
    def test_code_missing(self, tmp_path):
        row = _make_row(0)
        r = _eval_one(row, generated_dir=tmp_path, use_gt=False, timeout_sec=30)
        assert r["status"] == "code_missing"
        assert r["reward"] == 0.0

    def test_no_source(self):
        row = _make_row(0)
        r = _eval_one(row, generated_dir=None, use_gt=False, timeout_sec=30)
        assert r["status"] == "no_source"

    def test_exec_failed(self, tmp_path):
        row = _make_row(0)
        code_path = tmp_path / "test_0000.py"
        code_path.write_text("this is not valid python!!! syntax error", encoding="utf-8")
        with patch(
            "scripts.rl.benchmark._execute_cadquery_script",
            return_value=(False, "SyntaxError"),
        ):
            r = _eval_one(row, generated_dir=tmp_path, use_gt=False, timeout_sec=30)
        assert r["status"] == "exec_failed"
        assert r["reward"] == 0.0

    def test_use_gt_no_code(self):
        row = {"id": "x", "messages": []}
        r = _eval_one(row, generated_dir=None, use_gt=True, timeout_sec=30)
        assert r["status"] == "no_gt_code"

    def test_success_with_iou(self, tmp_path):
        row = _make_row(1)
        code_path = tmp_path / "test_0001.py"
        code_path.write_text("# generated code", encoding="utf-8")

        with (
            patch(
                "scripts.rl.benchmark._execute_cadquery_script",
                side_effect=[(True, None), (True, None)],
            ),
            patch(
                "scripts.rl.benchmark._compute_iou",
                return_value=(0.95, None),
            ),
        ):
            r = _eval_one(row, generated_dir=tmp_path, use_gt=False, timeout_sec=30)
        assert r["status"] == "ok"
        assert abs(r["iou"] - 0.95) < 1e-6
        assert abs(r["reward"] - 0.95) < 1e-6

    def test_iou_error(self, tmp_path):
        row = _make_row(1)
        code_path = tmp_path / "test_0001.py"
        code_path.write_text("# code", encoding="utf-8")

        with (
            patch(
                "scripts.rl.benchmark._execute_cadquery_script",
                side_effect=[(True, None), (True, None)],
            ),
            patch(
                "scripts.rl.benchmark._compute_iou",
                return_value=(0.0, "degenerate shape"),
            ),
        ):
            r = _eval_one(row, generated_dir=tmp_path, use_gt=False, timeout_sec=30)
        assert r["status"] == "iou_error"


class TestSummarise:
    def test_basic_summary(self, tmp_path):
        results = [
            {"id": "a", "status": "ok", "reward": 0.95, "iou": 0.95, "exec_sec": 1.0},
            {"id": "b", "status": "ok", "reward": 0.80, "iou": 0.80, "exec_sec": 2.0},
            {"id": "c", "status": "exec_failed", "reward": 0.0, "exec_sec": 0.5},
            {"id": "d", "status": "code_missing", "reward": 0.0, "exec_sec": 0.0},
        ]
        out = tmp_path / "bench.json"
        s = _summarise(results, out)
        assert s["total"] == 4
        assert s["pass_rate"] == 0.5  # 2/4
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["total"] == 4

    def test_empty_results(self, tmp_path):
        out = tmp_path / "bench.json"
        s = _summarise([], out)
        assert s["total"] == 0
        assert s["pass_rate"] == 0.0
        assert s["iou_mean"] == 0.0
