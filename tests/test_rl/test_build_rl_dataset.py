"""Tests for scripts/rl/build_rl_dataset.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.rl.build_rl_dataset import (
    _strip_assistant,
    build_from_gencad,
    build_rl_dataset,
)


class TestStripAssistant:
    def test_removes_assistant_turn(self):
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "assistant", "content": "code"},
        ]
        result = _strip_assistant(msgs)
        assert len(result) == 2
        assert all(m["role"] != "assistant" for m in result)

    def test_no_assistant_unchanged(self):
        msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
        assert _strip_assistant(msgs) == msgs


def _make_gencad_jsonl(tmp: Path, n: int = 5) -> Path:
    p = tmp / "sft_gencad.jsonl"
    with p.open("w") as f:
        for i in range(n):
            row = {
                "id": f"0000/{i:08d}",
                "task": "IMG2CQ",
                "source": "gencad",
                "split": "train" if i < 4 else "val",
                "messages": [
                    {"role": "system", "content": "sys"},
                    {"role": "user", "content": [{"type": "image", "path": f"/img/{i}.jpg"}]},
                    {"role": "assistant", "content": f"import cadquery as cq\nsolid{i}=..."},
                ],
            }
            f.write(json.dumps(row) + "\n")
    return p


class TestBuildFromGencad:
    def test_adds_rows_for_train_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 5)
            out: list[dict] = []
            stats = build_from_gencad(jsonl, None, out, splits=("train",))
        assert stats["added"] == 4
        assert all(r["split"] == "train" for r in out)

    def test_strips_assistant_from_prompt_msgs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 2)
            out: list[dict] = []
            build_from_gencad(jsonl, None, out, splits=("train", "val"))
        for row in out:
            assert all(m["role"] != "assistant" for m in row["prompt_msgs"])

    def test_gt_step_none_when_no_step_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 2)
            out: list[dict] = []
            build_from_gencad(jsonl, None, out)
        assert all(r["gt_step_path"] is None for r in out)

    def test_gt_step_populated_when_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 1)
            step_dir = tmp / "steps"
            step_dir.mkdir()
            step_file = step_dir / "0000" / "00000000.step"
            step_file.parent.mkdir(parents=True)
            step_file.write_text("dummy")
            out: list[dict] = []
            build_from_gencad(jsonl, step_dir, out, splits=("train",))
        assert out[0]["gt_step_path"] == str(step_file)

    def test_limit_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 10)
            out: list[dict] = []
            stats = build_from_gencad(jsonl, None, out, splits=("train", "val"), limit=3)
        assert stats["added"] == 3

    def test_source_field_is_gencad(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 2)
            out: list[dict] = []
            build_from_gencad(jsonl, None, out)
        assert all(r["source"] == "gencad" for r in out)


class TestBuildRlDataset:
    def test_output_file_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 3)
            out_dir = tmp / "rl"
            stats = build_rl_dataset(out_dir, gencad_jsonl=jsonl)
            assert (out_dir / "rl_dataset.jsonl").exists()
            assert stats["total"] == 3

    def test_schema_fields_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jsonl = _make_gencad_jsonl(tmp, 2)
            out_dir = tmp / "rl"
            build_rl_dataset(out_dir, gencad_jsonl=jsonl)
            rows = [
                json.loads(l)
                for l in (out_dir / "rl_dataset.jsonl").read_text().splitlines()
                if l.strip()
            ]
        required = {"id", "source", "split", "task", "prompt_msgs", "gt_step_path", "gt_vol", "complexity_class"}
        for row in rows:
            assert required <= set(row.keys())

    def test_no_sources_produces_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "rl"
            stats = build_rl_dataset(out_dir)
        assert stats["total"] == 0
