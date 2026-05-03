"""Unit tests for bench.models.prompts — text helpers + parsers.

Covers strip_fences, parse_qa_answers, build_qa_user_text, build_edit_user_text.
"""

from __future__ import annotations

import pytest

from bench.models.prompts import (
    build_edit_user_text,
    build_qa_user_text,
    parse_qa_answers,
    strip_fences,
)

# ── strip_fences ──────────────────────────────────────────────────────────────


class TestStripFences:
    def test_no_fences(self):
        assert strip_fences("x = 1") == "x = 1"

    def test_plain_fences(self):
        assert strip_fences("```\nx = 1\n```") == "x = 1"

    def test_python_fences(self):
        assert strip_fences("```python\nx = 1\n```") == "x = 1"

    def test_preserves_inner_newlines(self):
        assert strip_fences("```python\na = 1\nb = 2\n```") == "a = 1\nb = 2"

    def test_strips_leading_trailing_whitespace(self):
        assert strip_fences("\n\n  x = 1  \n\n") == "x = 1"

    def test_handles_no_inner_content(self):
        assert strip_fences("```\n```") == ""

    def test_non_python_lang_marker_partially_stripped(self):
        # Regex strips ``` (and optional 'python'), leaves any other lang token
        assert strip_fences("```js\nfoo()\n```") == "js\nfoo()"


# ── parse_qa_answers ──────────────────────────────────────────────────────────


class TestParseQaAnswers:
    def test_simple_array(self):
        assert parse_qa_answers("[1, 2, 3]", n_expected=3) == [1.0, 2.0, 3.0]

    def test_decimals(self):
        assert parse_qa_answers("[2.5, 0.75]", n_expected=2) == [2.5, 0.75]

    def test_with_json_fences(self):
        raw = "```json\n[10, 20]\n```"
        assert parse_qa_answers(raw, n_expected=2) == [10.0, 20.0]

    def test_with_plain_fences(self):
        raw = "```\n[1.5]\n```"
        assert parse_qa_answers(raw, n_expected=1) == [1.5]

    def test_extra_whitespace(self):
        assert parse_qa_answers("  [42]  ", n_expected=1) == [42.0]

    def test_mismatched_length_returns_none(self):
        assert parse_qa_answers("[1, 2, 3]", n_expected=2) is None

    def test_empty_array_returns_none_when_expected_nonzero(self):
        assert parse_qa_answers("[]", n_expected=1) is None

    def test_no_array_returns_none(self):
        assert parse_qa_answers("hello world", n_expected=1) is None

    def test_invalid_json_returns_none(self):
        assert parse_qa_answers("[1, 2, NOT_A_NUMBER]", n_expected=3) is None

    def test_string_in_array_returns_none(self):
        # Non-numeric element fails float() coercion
        assert parse_qa_answers('[1, "abc"]', n_expected=2) is None

    def test_zero_expected_with_empty_array(self):
        assert parse_qa_answers("[]", n_expected=0) == []

    def test_picks_first_array_in_text(self):
        # Regex picks first match
        result = parse_qa_answers("blah [1, 2] more text [3, 4]", n_expected=2)
        assert result == [1.0, 2.0]

    def test_nested_arrays_break_simple_regex(self):
        # The regex \[[^\[\]]*\] forbids inner brackets
        # → only simple flat arrays parse
        result = parse_qa_answers("[[1, 2], [3]]", n_expected=2)
        # Inner first-bracket [1, 2] would parse first
        # Either it returns [1, 2] or None
        assert result in (None, [1.0, 2.0])

    def test_int_strings_coerced(self):
        # JSON ints are already int; float() coerces fine
        assert parse_qa_answers("[12, 34]", n_expected=2) == [12.0, 34.0]


# ── build_qa_user_text ────────────────────────────────────────────────────────


class TestBuildQaUserText:
    def test_with_code(self):
        text = build_qa_user_text(["How many holes?"], code="result = cq.Workplane()")
        assert "How many holes?" in text
        assert "result = cq.Workplane()" in text

    def test_without_code(self):
        text = build_qa_user_text(["What is X?", "What is Y?"])
        assert "What is X?" in text
        assert "What is Y?" in text

    def test_questions_listed(self):
        questions = ["q1", "q2", "q3"]
        text = build_qa_user_text(questions)
        for q in questions:
            assert q in text


# ── build_edit_user_text ──────────────────────────────────────────────────────


class TestBuildEditUserText:
    def test_includes_orig_code(self):
        text = build_edit_user_text(
            "result = cq.Workplane().box(10,10,10)", "make it bigger"
        )
        assert "result = cq.Workplane().box(10,10,10)" in text

    def test_includes_instruction(self):
        text = build_edit_user_text("orig", "double the height")
        assert "double the height" in text

    def test_python_code_fenced(self):
        text = build_edit_user_text("x = 1", "change x")
        # build_edit_user_text wraps orig in ```python ... ```
        assert "```python" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
