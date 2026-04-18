"""Tests for build_verified_pairs.py data pipeline.

Unit tests only — no real STEP/JSON files required.
"""

from __future__ import annotations

from pathlib import Path

# ── module under test ────────────────────────────────────────────────────────
import pytest

from scripts.data_generation.build_verified_pairs import (
    _append_skipped,
    _build_index,
    _classify_complexity,
    _ensure_export_line,
    _generate_code_rule_based,
    _parse_svg_dim,
    _parse_visual_verdict,
    _patch_output_step_path,
    _repo_rel,
    _strip_markdown_fences,
    _trim_extrude,
    _trim_json_for_prompt,
    _trim_sketch,
    _within_rel_tol,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── _strip_markdown_fences ───────────────────────────────────────────────────


class TestStripMarkdownFences:
    def test_no_fences(self):
        assert _strip_markdown_fences("x = 1") == "x = 1"

    def test_plain_fences(self):
        code = "```\nx = 1\n```"
        assert _strip_markdown_fences(code) == "x = 1"

    def test_python_fences(self):
        code = "```python\nx = 1\n```"
        assert _strip_markdown_fences(code) == "x = 1"

    def test_preserves_inner_newlines(self):
        code = "```python\na = 1\nb = 2\n```"
        assert _strip_markdown_fences(code) == "a = 1\nb = 2"


# ── _ensure_export_line ──────────────────────────────────────────────────────


class TestEnsureExportLine:
    def test_adds_missing_export(self):
        code = "result = cq.Workplane().box(1,1,1)"
        out = _ensure_export_line(code)
        assert out.endswith("result.val().exportStep('output.step')\n")

    def test_no_duplicate_when_present(self):
        code = "result = x\nresult.val().exportStep('output.step')"
        out = _ensure_export_line(code)
        assert out.count("exportStep") == 1

    def test_newline_terminated(self):
        code = "result = x\nresult.val().exportStep('output.step')"
        assert _ensure_export_line(code).endswith("\n")


# ── _patch_output_step_path ──────────────────────────────────────────────────


class TestPatchOutputStepPath:
    def test_replaces_single_quoted(self):
        code = "result.val().exportStep('output.step')"
        patched = _patch_output_step_path(code, Path("/tmp/out.step"))
        assert "'/tmp/out.step'" in patched

    def test_replaces_double_quoted(self):
        code = 'result.val().exportStep("output.step")'
        patched = _patch_output_step_path(code, Path("/tmp/out.step"))
        assert "/tmp/out.step" in patched

    def test_adds_export_when_missing(self):
        code = "result = cq.Workplane().box(1,1,1)"
        patched = _patch_output_step_path(code, Path("/tmp/out.step"))
        assert "exportStep" in patched


# ── _within_rel_tol ──────────────────────────────────────────────────────────


class TestWithinRelTol:
    def test_exact_match(self):
        assert _within_rel_tol(5.0, 5.0, 0.10) is True

    def test_within_tolerance(self):
        assert _within_rel_tol(5.45, 5.0, 0.10) is True

    def test_outside_tolerance(self):
        assert _within_rel_tol(6.0, 5.0, 0.10) is False

    def test_zero_target(self):
        assert _within_rel_tol(0.0, 0.0, 0.10) is True
        assert _within_rel_tol(1e-5, 0.0, 0.10) is False


# ── _trim_json_for_prompt ────────────────────────────────────────────────────


class TestTrimJsonForPrompt:
    def test_keeps_sketch_and_extrude(self):
        data = {
            "timeline": ["e1", "e2"],
            "entities": {
                "e1": {"type": "Sketch", "data": "x"},
                "e2": {"type": "ExtrudeFeature", "data": "y"},
                "e3": {"type": "BooleanFeature", "data": "z"},
            },
        }
        result = _trim_json_for_prompt(data)
        assert "e1" in result["entities"]
        assert "e2" in result["entities"]
        assert "e3" not in result["entities"]

    def test_uses_sequence_if_no_timeline(self):
        data = {"sequence": [1, 2], "entities": {}}
        result = _trim_json_for_prompt(data)
        assert result["timeline"] == [1, 2]

    def test_empty_entities(self):
        result = _trim_json_for_prompt({"entities": {}})
        assert result["entities"] == {}


# ── _trim_sketch / _trim_extrude ─────────────────────────────────────────────


class TestTrimSketch:
    def _make_sketch(self):
        return {
            "name": "Sketch1",
            "type": "Sketch",
            "points": {"p1": {"x": 0, "y": 0}},
            "curves": {"c1": {"type": "Line"}},
            "constraints": {"co1": {"type": "Fix"}},
            "dimensions": {"d1": {"value": 5.0}},
            "transform": {"origin": {"x": 0, "y": 0, "z": 0}},
            "reference_plane": {
                "type": "ConstructionPlane",
                "name": "XY",
                "plane": {"origin": {"x": 0}},
                "corrective_transform": {"matrix": []},
            },
            "profiles": {
                "pid1": {
                    "loops": [
                        {
                            "is_outer": True,
                            "profile_curves": [
                                {
                                    "type": "Circle3D",
                                    "radius": 3.0,
                                    "curve": "uuid-abc",
                                },
                            ],
                        }
                    ]
                }
            },
        }

    def test_drops_raw_geometry_arrays(self):
        out = _trim_sketch(self._make_sketch())
        assert "points" not in out
        assert "curves" not in out
        assert "constraints" not in out
        assert "dimensions" not in out

    def test_keeps_name_type_transform(self):
        out = _trim_sketch(self._make_sketch())
        assert out["name"] == "Sketch1"
        assert out["type"] == "Sketch"
        assert "transform" in out

    def test_drops_corrective_transform(self):
        out = _trim_sketch(self._make_sketch())
        assert "corrective_transform" not in out["reference_plane"]
        assert out["reference_plane"]["name"] == "XY"

    def test_drops_curve_uuid_from_profile_curves(self):
        out = _trim_sketch(self._make_sketch())
        pc = out["profiles"]["pid1"]["loops"][0]["profile_curves"][0]
        assert "curve" not in pc
        assert pc["type"] == "Circle3D"
        assert pc["radius"] == 3.0


class TestTrimExtrude:
    def _make_extrude(self):
        return {
            "name": "Extrude1",
            "type": "ExtrudeFeature",
            "operation": "NewBodyFeatureOperation",
            "extent_type": "SymmetricFeatureExtentType",
            "profiles": [{"profile": "pid1", "sketch": "sid1"}],
            "extent_one": {
                "type": "SymmetricExtentDefinition",
                "distance": {"type": "ModelParameter", "value": 5.0, "name": "d1"},
                "taper_angle": {"value": 0.0},
                "is_full_length": False,
            },
            "start_extent": {"type": "ProfilePlaneStartDefinition", "extra": "data"},
            "faces": [{"id": "f1"}],
            "bodies": [{"id": "b1"}],
            "extrude_bodies": [{"id": "eb1"}],
            "extrude_faces": [{"id": "ef1"}],
            "extrude_side_faces": [],
            "extrude_end_faces": [],
            "extrude_start_faces": [],
        }

    def test_drops_face_body_arrays(self):
        out = _trim_extrude(self._make_extrude())
        for key in (
            "faces",
            "bodies",
            "extrude_bodies",
            "extrude_faces",
            "extrude_side_faces",
            "extrude_end_faces",
            "extrude_start_faces",
        ):
            assert key not in out

    def test_keeps_operation_and_profiles(self):
        out = _trim_extrude(self._make_extrude())
        assert out["operation"] == "NewBodyFeatureOperation"
        assert out["profiles"] == [{"profile": "pid1", "sketch": "sid1"}]

    def test_slims_extent_one_to_type_and_value(self):
        out = _trim_extrude(self._make_extrude())
        assert out["extent_one"] == {
            "type": "SymmetricExtentDefinition",
            "distance": {"value": 5.0},
        }

    def test_slims_start_extent_to_type(self):
        out = _trim_extrude(self._make_extrude())
        assert out["start_extent"] == {"type": "ProfilePlaneStartDefinition"}


# ── _classify_complexity ─────────────────────────────────────────────────────


class TestClassifyComplexity:
    def test_no_sketches_is_box(self):
        assert _classify_complexity({"entities": {}}) == "box"

    def test_single_circle_sketch_is_cylinder(self):
        data = {
            "entities": {
                "s1": {
                    "type": "Sketch",
                    "profiles": {
                        "p1": {"loops": [{"profile_curves": [{"type": "Circle3D"}]}]}
                    },
                }
            }
        }
        assert _classify_complexity(data) == "cylinder"

    def test_multiple_sketches_is_complex(self):
        def make_sketch(name):
            return {
                name: {
                    "type": "Sketch",
                    "profiles": {
                        "p": {"loops": [{"profile_curves": [{"type": "Line3D"}]}]}
                    },
                }
            }

        entities = {}
        entities.update(make_sketch("s1"))
        entities.update(make_sketch("s2"))
        assert _classify_complexity({"entities": entities}) == "complex"

    def test_mixed_curves_is_complex(self):
        data = {
            "entities": {
                "s1": {
                    "type": "Sketch",
                    "profiles": {
                        "p1": {
                            "loops": [
                                {
                                    "profile_curves": [
                                        {"type": "Line3D"},
                                        {"type": "Arc3D"},
                                    ]
                                }
                            ]
                        }
                    },
                }
            }
        }
        assert _classify_complexity(data) == "complex"


# ── _append_skipped ──────────────────────────────────────────────────────────


class TestAppendSkipped:
    def test_creates_file_and_appends(self, tmp_path):
        skipped = tmp_path / "sub" / "skipped.txt"
        _append_skipped(skipped, "part_001", "render", "cairo missing")
        assert skipped.exists()
        lines = skipped.read_text().splitlines()
        assert lines[0] == "part_001\trender\tcairo missing"

    def test_multiple_appends(self, tmp_path):
        skipped = tmp_path / "skipped.txt"
        _append_skipped(skipped, "a", "s1", "r1")
        _append_skipped(skipped, "b", "s2", "r2")
        lines = skipped.read_text().splitlines()
        assert len(lines) == 2


# ── _parse_svg_dim ───────────────────────────────────────────────────────────


class TestParseSvgDim:
    def test_numeric(self):
        assert _parse_svg_dim("400") == 400.0

    def test_px_suffix(self):
        assert _parse_svg_dim("600px") == 600.0

    def test_none_returns_fallback(self):
        assert _parse_svg_dim(None) == 1.0

    def test_invalid_returns_fallback(self):
        assert _parse_svg_dim("abc") == 1.0

    def test_zero_returns_fallback(self):
        assert _parse_svg_dim("0") == 1.0


# ── _build_index ─────────────────────────────────────────────────────────────


class TestBuildIndex:
    def test_matches_json_to_step(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        (step_dir / "part_001_3e.step").write_text("ISO")
        (json_dir / "part_001.json").write_text("{}")

        records = _build_index(json_dir, step_dir, limit=0)
        assert len(records) == 1
        assert records[0].base_stem == "part_001"
        assert records[0].stem == "part_001_3e"

    def test_picks_last_step(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        (step_dir / "part_001_1e.step").write_text("ISO")
        (step_dir / "part_001_3e.step").write_text("ISO")
        (json_dir / "part_001.json").write_text("{}")

        records = _build_index(json_dir, step_dir, limit=0)
        assert records[0].stem == "part_001_3e"

    def test_limit_respected(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        for i in range(5):
            (step_dir / f"part_{i:03d}_1e.step").write_text("ISO")
            (json_dir / f"part_{i:03d}.json").write_text("{}")

        records = _build_index(json_dir, step_dir, limit=3)
        assert len(records) == 3

    def test_no_match_skipped(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        (json_dir / "part_001.json").write_text("{}")
        # No corresponding STEP

        records = _build_index(json_dir, step_dir, limit=0)
        assert records == []

    def test_ignores_non_matching_step_names(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        (step_dir / "part_001.step").write_text("ISO")  # no _Ne suffix
        (json_dir / "part_001.json").write_text("{}")

        records = _build_index(json_dir, step_dir, limit=0)
        assert records == []


# ── _repo_rel ────────────────────────────────────────────────────────────────


class TestRepoRel:
    def test_returns_relative_for_repo_path(self):
        path = REPO_ROOT / "scripts" / "data_generation" / "build_verified_pairs.py"
        rel = _repo_rel(path)
        assert not rel.startswith("/")
        assert "build_verified_pairs.py" in rel

    def test_returns_abs_for_outside_path(self, tmp_path):
        result = _repo_rel(tmp_path / "file.txt")
        assert result.startswith("/")


# ── _generate_code_rule_based ────────────────────────────────────────────────


class TestGenerateCodeRuleBased:
    def test_unavailable_returns_error(self, tmp_path):
        code, err = _generate_code_rule_based(tmp_path / "x.json", {}, fallback_fn=None)
        assert code is None
        assert "unavailable" in err

    def test_calls_fallback_fn(self, tmp_path):
        def fake_fn(json_path, json_data):
            return "result = cq.Workplane().box(1,1,1)"

        code, err = _generate_code_rule_based(
            tmp_path / "x.json", {}, fallback_fn=fake_fn
        )
        assert code is not None
        assert err is None
        assert "exportStep" in code

    def test_fallback_exception_returns_error(self, tmp_path):
        def bad_fn(json_path, json_data):
            raise RuntimeError("broken")

        code, err = _generate_code_rule_based(
            tmp_path / "x.json", {}, fallback_fn=bad_fn
        )
        assert code is None
        assert "broken" in err

    def test_empty_code_returns_error(self, tmp_path):
        code, err = _generate_code_rule_based(
            tmp_path / "x.json", {}, fallback_fn=lambda p, d: ""
        )
        assert code is None


# ── _parse_visual_verdict ────────────────────────────────────────────────────


class TestParseVisualVerdict:
    def test_json_pass(self):
        text = '{"verdict": "PASS", "reason": "identical", "views_checked": ["front"]}'
        verdict, reason = _parse_visual_verdict(text)
        assert verdict == "PASS"
        assert reason == "identical"

    def test_json_fail(self):
        text = '{"verdict": "FAIL", "reason": "missing pocket", "views_checked": ["front"]}'
        verdict, reason = _parse_visual_verdict(text)
        assert verdict == "FAIL"
        assert reason == "missing pocket"

    def test_plain_pass_keyword(self):
        text = "VERDICT: PASS\nThe parts look identical."
        verdict, reason = _parse_visual_verdict(text)
        assert verdict == "PASS"

    def test_plain_fail_keyword(self):
        text = "VERDICT: FAIL\nThe hole placement differs."
        verdict, reason = _parse_visual_verdict(text)
        assert verdict == "FAIL"

    def test_no_verdict_defaults_fail(self):
        text = "I cannot determine the difference."
        verdict, reason = _parse_visual_verdict(text)
        assert verdict == "FAIL"

    def test_json_embedded_in_text(self):
        text = (
            "After reviewing the images:\n"
            '{"verdict": "PASS", "reason": "both identical", "views_checked": []}\n'
            "End of analysis."
        )
        verdict, reason = _parse_visual_verdict(text)
        assert verdict == "PASS"


# ── _compute_iou (requires cadquery) ─────────────────────────────────────────


def _has_cadquery() -> bool:
    try:
        import cadquery  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_cadquery(), reason="cadquery not available")
class TestComputeIou:
    """Integration tests — skipped when cadquery / libGL absent."""

    def test_identical_shapes_iou_one(self, tmp_path):
        from scripts.data_generation.build_verified_pairs import (
            GT_STEP_DIR,
            _compute_iou,
        )

        step_dir = GT_STEP_DIR
        steps = list(step_dir.glob("*.step"))
        if not steps:
            pytest.skip(f"no STEP files found in {step_dir}")
        step = steps[0]
        iou, err = _compute_iou(step, step)
        assert err is None
        assert abs(iou - 1.0) < 1e-4

    def test_returns_float_between_0_and_1(self, tmp_path):
        from scripts.data_generation.build_verified_pairs import _compute_iou

        steps = list(
            Path(
                "/workspace/data/data_generation/open_source/fusion360_gallery/raw"
                "/r1.0.1_extrude_tools/extrude_tools"
            ).glob("*.step")
        )[:2]
        if len(steps) < 2:
            pytest.skip("need at least 2 STEP files")
        iou, err = _compute_iou(steps[0], steps[1])
        assert err is None or isinstance(err, str)
        assert 0.0 <= iou <= 1.0

    def test_missing_file_returns_error(self, tmp_path):
        from scripts.data_generation.build_verified_pairs import _compute_iou

        iou, err = _compute_iou(
            tmp_path / "nonexistent.step", tmp_path / "also_none.step"
        )
        assert err is not None
        assert iou == 0.0


# ── _refine_code_with_feedback ────────────────────────────────────────────────


class TestRefineCodeWithFeedback:
    def test_returns_none_when_no_api_key(self, monkeypatch):
        """No API keys -> (None, initial_iou, 0) immediately."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY1", raising=False)
        from scripts.data_generation.build_verified_pairs import (
            _refine_code_with_feedback,
        )

        best_code, best_iou, rounds = _refine_code_with_feedback(
            json_data={},
            initial_code="result = None",
            gt_step_path=Path("/nonexistent/gt.step"),
            gen_step_path=Path("/nonexistent/gen.step"),
            initial_iou=0.5,
        )
        assert best_code is None
        assert best_iou == 0.5
        assert rounds == 0

    def test_returns_initial_on_import_error(self, monkeypatch):
        """If openai can't be imported, return (None, initial_iou, 0)."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("openai not installed")
            return real_import(name, *args, **kwargs)

        from scripts.data_generation.build_verified_pairs import (
            _refine_code_with_feedback,
        )

        monkeypatch.setattr(builtins, "__import__", mock_import)
        best_code, best_iou, rounds = _refine_code_with_feedback(
            json_data={},
            initial_code="result = None",
            gt_step_path=Path("/nonexistent/gt.step"),
            gen_step_path=Path("/nonexistent/gen.step"),
            initial_iou=0.7,
        )
        assert best_code is None
        assert best_iou == 0.7
        assert rounds == 0

    def test_signature_correct(self):
        """Function exists and has expected parameters."""
        import inspect

        from scripts.data_generation.build_verified_pairs import (
            _refine_code_with_feedback,
        )

        sig = inspect.signature(_refine_code_with_feedback)
        params = list(sig.parameters.keys())
        assert "json_data" in params
        assert "initial_code" in params
        assert "gt_step_path" in params
        assert "gen_step_path" in params
        assert "initial_iou" in params
        assert "model" in params
        assert "max_rounds" in params
        assert "iou_threshold" in params

    def test_iou_threshold_constant_exported(self):
        """IOU_THRESHOLD is exported from build_verified_pairs."""
        from scripts.data_generation.build_verified_pairs import IOU_THRESHOLD

        assert IOU_THRESHOLD == 0.99


class TestGetApiKeys:
    def test_returns_primary_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-primary")
        monkeypatch.delenv("OPENAI_API_KEY1", raising=False)
        from scripts.data_generation.build_verified_pairs import _get_api_keys

        keys = _get_api_keys()
        assert keys == ["sk-primary"]

    def test_returns_both_keys(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-primary")
        monkeypatch.setenv("OPENAI_API_KEY1", "sk-backup")
        from scripts.data_generation.build_verified_pairs import _get_api_keys

        keys = _get_api_keys()
        assert keys == ["sk-primary", "sk-backup"]

    def test_returns_empty_when_none_set(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY1", raising=False)
        from scripts.data_generation.build_verified_pairs import _get_api_keys

        assert _get_api_keys() == []

    def test_skips_blank_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "  ")
        monkeypatch.delenv("OPENAI_API_KEY1", raising=False)
        from scripts.data_generation.build_verified_pairs import _get_api_keys

        assert _get_api_keys() == []


class TestClassifyErrorType:
    def test_oauth_error(self):
        from scripts.data_generation.build_verified_pairs import _classify_error_type

        assert _classify_error_type("OAuth flow failed") == "oauth_error"

    def test_codex_auth_error(self):
        from scripts.data_generation.build_verified_pairs import _classify_error_type

        assert _classify_error_type("codex exit=1: auth required") == "codex_auth_error"

    def test_rate_limit(self):
        from scripts.data_generation.build_verified_pairs import _classify_error_type

        assert _classify_error_type("rate limit exceeded 429") == "rate_limit"

    def test_model_not_found(self):
        from scripts.data_generation.build_verified_pairs import _classify_error_type

        assert _classify_error_type("model codex-mini-latest not found") == "model_not_found"

    def test_timeout(self):
        from scripts.data_generation.build_verified_pairs import _classify_error_type

        assert _classify_error_type("timed out after 300s") == "timeout"

    def test_other(self):
        from scripts.data_generation.build_verified_pairs import _classify_error_type

        assert _classify_error_type("some unknown error") == "other"


class TestGenerateCodeClaude:
    def test_returns_error_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from scripts.data_generation.build_verified_pairs import _generate_code_claude

        code, err = _generate_code_claude({})
        assert code is None
        assert "ANTHROPIC_API_KEY" in (err or "")

    def test_signature(self):
        import inspect

        from scripts.data_generation.build_verified_pairs import _generate_code_claude

        sig = inspect.signature(_generate_code_claude)
        params = list(sig.parameters)
        assert "json_data" in params
        assert "model" in params
        assert sig.parameters["model"].default == "claude-sonnet-4-6"


class TestRefineCodeWithClaudeFeedback:
    def test_returns_none_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from scripts.data_generation.build_verified_pairs import (
            _refine_code_with_claude_feedback,
        )

        code, iou, rounds = _refine_code_with_claude_feedback(
            json_data={},
            initial_code="result = None",
            gt_step_path=Path("/nonexistent/gt.step"),
            gen_step_path=Path("/nonexistent/gen.step"),
            initial_iou=0.5,
        )
        assert code is None
        assert iou == 0.5
        assert rounds == 0

    def test_signature(self):
        import inspect

        from scripts.data_generation.build_verified_pairs import (
            _refine_code_with_claude_feedback,
        )

        sig = inspect.signature(_refine_code_with_claude_feedback)
        params = list(sig.parameters)
        assert "json_data" in params
        assert "model" in params
        assert sig.parameters["model"].default == "claude-sonnet-4-6"


class TestBuildIndexOffset:
    def test_offset_skips_first_n(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        for i in range(5):
            (step_dir / f"part_{i:03d}_1e.step").write_text("ISO")
            (json_dir / f"part_{i:03d}.json").write_text("{}")

        records = _build_index(json_dir, step_dir, limit=0, offset=2)
        assert len(records) == 3
        assert records[0].base_stem == "part_002"

    def test_offset_with_limit(self, tmp_path):
        step_dir = tmp_path / "steps"
        json_dir = tmp_path / "jsons"
        step_dir.mkdir()
        json_dir.mkdir()

        for i in range(10):
            (step_dir / f"part_{i:03d}_1e.step").write_text("ISO")
            (json_dir / f"part_{i:03d}.json").write_text("{}")

        records = _build_index(json_dir, step_dir, limit=3, offset=5)
        assert len(records) == 3
        assert records[0].base_stem == "part_005"

    def test_ocp_hashcode_fix_prepended(self):
        from scripts.data_generation.build_verified_pairs import _patch_output_step_path

        code = "import cadquery as cq\nresult = cq.Workplane()\nresult.val().exportStep('output.step')"
        patched = _patch_output_step_path(code, Path("/tmp/out.step"))
        assert "Standard_Transient" in patched
        assert "__hash__" in patched
