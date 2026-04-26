"""Unit tests for bench.results.ResultsDir.

Covers append-only dedup, key normalization (slug), provenance logging,
artifact saving (code/step/render dir), and context-manager lifecycle.
"""

from __future__ import annotations

import json

import pytest

from bench.results import ResultsDir, slug

# ── slug ──────────────────────────────────────────────────────────────────────


class TestSlug:
    def test_no_special_chars(self):
        assert slug("gpt-4o") == "gpt-4o"

    def test_colon_replaced(self):
        assert slug("local:./checkpoints/foo") == "local_._checkpoints_foo"

    def test_slash_replaced(self):
        assert slug("openai/gpt-5") == "openai_gpt-5"

    def test_space_replaced(self):
        assert slug("my model v2") == "my_model_v2"

    def test_all_three(self):
        assert slug("a:b/c d") == "a_b_c_d"


# ── ResultsDir basic ──────────────────────────────────────────────────────────


class TestResultsDirInit:
    def test_creates_root_and_runs(self, tmp_path):
        rd = ResultsDir("img2cq", "gpt-4o", root=tmp_path)
        assert rd.root.exists()
        assert rd.runs.exists()
        assert rd.task == "img2cq"
        assert rd.model == "gpt-4o"

    def test_slug_applied_to_model_dir(self, tmp_path):
        rd = ResultsDir("qa_img", "openai/gpt-5", root=tmp_path)
        assert rd.root.name == "openai_gpt-5"


# ── append + done_keys (dedup pool) ───────────────────────────────────────────


class TestAppendAndDedup:
    def test_done_keys_empty_initially(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        assert rd.done_keys() == set()

    def test_append_writes_and_done_keys_reads(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        with rd:
            rd.append({"stem": "s1", "iou": 0.9})
            rd.append({"stem": "s2", "iou": 0.5})
        assert rd.done_keys() == {"s1", "s2"}

    def test_done_keys_alternative_id_key(self, tmp_path):
        rd = ResultsDir("edit_code", "m1", root=tmp_path)
        with rd:
            rd.append({"record_id": "r1", "score": 0.8})
            rd.append({"record_id": "r2", "score": 0.7})
        assert rd.done_keys(id_key="record_id") == {"r1", "r2"}

    def test_appending_appends_not_overwrites(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        with rd:
            rd.append({"stem": "s1", "iou": 0.5})
        # Re-open + append more
        rd2 = ResultsDir("img2cq", "m1", root=tmp_path)
        with rd2:
            rd2.append({"stem": "s2", "iou": 0.6})
        assert rd2.done_keys() == {"s1", "s2"}

    def test_done_keys_skips_missing_id(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        with rd:
            rd.append({"stem": "s1"})
            rd.append({"no_id": "x"})  # no stem field — skipped
        assert rd.done_keys() == {"s1"}

    def test_done_keys_skips_invalid_json_lines(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        rd.results_path.parent.mkdir(parents=True, exist_ok=True)
        # Manually write a corrupt line + valid line
        rd.results_path.write_text('{"stem": "s1"}\nNOT_JSON\n{"stem": "s2"}\n')
        # done_keys must skip the bad line gracefully
        assert rd.done_keys() == {"s1", "s2"}

    def test_done_keys_skips_blank_lines(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        rd.results_path.parent.mkdir(parents=True, exist_ok=True)
        rd.results_path.write_text('{"stem": "s1"}\n\n\n{"stem": "s2"}\n')
        assert rd.done_keys() == {"s1", "s2"}


# ── save_code / save_step / save_render_dir ───────────────────────────────────


class TestSaveArtifacts:
    def test_save_code(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        p = rd.save_code("s1", "import cadquery as cq\nresult = cq.Workplane()")
        assert p.exists()
        assert p.read_text().startswith("import cadquery")

    def test_save_step_copies_file(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        src = tmp_path / "src.step"
        src.write_text("ISO-10303-21;\n...content...")
        p = rd.save_step("s1", src)
        assert p.exists()
        assert p.read_text() == src.read_text()

    def test_save_render_dir_copies_recursively(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        src = tmp_path / "render_src"
        src.mkdir()
        (src / "view_0.png").write_bytes(b"fake_png_0")
        (src / "composite.png").write_bytes(b"fake_composite")
        target = rd.save_render_dir("s1", src)
        assert target.exists()
        assert (target / "view_0.png").read_bytes() == b"fake_png_0"
        assert (target / "composite.png").read_bytes() == b"fake_composite"

    def test_save_render_dir_overwrites_existing(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        src1 = tmp_path / "r1"
        src1.mkdir()
        (src1 / "a.png").write_bytes(b"first")
        rd.save_render_dir("s1", src1)
        # Second time with different content → fully replaced
        src2 = tmp_path / "r2"
        src2.mkdir()
        (src2 / "b.png").write_bytes(b"second")
        target = rd.save_render_dir("s1", src2)
        assert (target / "b.png").exists()
        assert not (target / "a.png").exists()


# ── log_run provenance ────────────────────────────────────────────────────────


class TestLogRun:
    def test_log_run_writes_sidecar_with_argv(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        argv = {"seed": 42, "limit": 10, "model": "m1"}
        sampled = [{"stem": "s1"}, {"stem": "s2"}]
        path = rd.log_run(argv, sampled=sampled)
        assert path.exists()
        rec = json.loads(path.read_text())
        assert rec["task"] == "img2cq"
        assert rec["model"] == "m1"
        assert rec["argv"] == argv
        assert rec["n_sampled"] == 2
        assert rec["keys"] == ["s1", "s2"]

    def test_log_run_filename_format(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        path = rd.log_run({"seed": 7, "limit": 5}, sampled=[{"stem": "x"}])
        # Format: <ts>__seed7__N5.json (n falls back to limit if no sampled)
        assert "seed7" in path.name
        assert path.name.endswith(".json")

    def test_log_run_uses_n_arg_when_no_sampled(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        path = rd.log_run({"seed": 1, "n": 100})
        assert "N100" in path.name

    def test_log_run_skips_rows_without_id(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        sampled = [{"stem": "s1"}, {"no_id": "x"}, {"stem": "s2"}]
        path = rd.log_run({"seed": 0, "limit": 3}, sampled=sampled)
        rec = json.loads(path.read_text())
        # Only 2 keys (the no_id row is skipped)
        assert rec["keys"] == ["s1", "s2"]
        assert rec["n_sampled"] == 2

    def test_log_run_custom_id_key(self, tmp_path):
        rd = ResultsDir("edit_code", "m1", root=tmp_path)
        sampled = [{"record_id": "r1"}, {"record_id": "r2"}]
        path = rd.log_run({"seed": 0, "limit": 2}, sampled=sampled, id_key="record_id")
        rec = json.loads(path.read_text())
        assert rec["keys"] == ["r1", "r2"]


# ── Context manager + open/close ──────────────────────────────────────────────


class TestContextManager:
    def test_with_block_opens_and_closes(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        with rd as fh:
            assert rd._fh is not None
            assert fh is rd  # __enter__ returns self
        assert rd._fh is None

    def test_explicit_open_close(self, tmp_path):
        rd = ResultsDir("img2cq", "m1", root=tmp_path)
        rd.open()
        assert rd._fh is not None
        rd.append({"stem": "s1"})
        rd.close()
        assert rd._fh is None
        # File still has the data
        assert "s1" in rd.results_path.read_text()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
