"""Tests for _is_valid_type covering PEP604 Union syntax."""

import types
from typing import Optional, Union

from src.verification.syntactic.schema import _is_valid_type


class TestIsValidTypePEP604:
    def test_str_or_none_with_str(self):
        assert _is_valid_type("hello", str | None) is True

    def test_str_or_none_with_none(self):
        assert _is_valid_type(None, str | None) is True

    def test_str_or_none_with_int(self):
        assert _is_valid_type(42, str | None) is False

    def test_union_str_none_with_str(self):
        assert _is_valid_type("hello", Union[str, None]) is True  # noqa: UP007

    def test_union_str_none_with_none(self):
        assert _is_valid_type(None, Union[str, None]) is True  # noqa: UP007

    def test_union_str_none_with_int(self):
        assert _is_valid_type(42, Union[str, None]) is False  # noqa: UP007

    def test_optional_list_str_with_list(self):
        assert _is_valid_type(["a", "b"], Optional[list[str]]) is True  # noqa: UP045

    def test_optional_list_str_with_none(self):
        assert _is_valid_type(None, Optional[list[str]]) is True  # noqa: UP045

    def test_optional_list_str_with_dict(self):
        assert _is_valid_type({}, Optional[list[str]]) is False  # noqa: UP045

    def test_union_type_is_recognized(self):
        """types.UnionType (PEP604) recognized as union."""
        t = str | int
        assert isinstance(t, types.UnionType)
        assert _is_valid_type("x", t) is True
        assert _is_valid_type(1, t) is True
        assert _is_valid_type([], t) is False
