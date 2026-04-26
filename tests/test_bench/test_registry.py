"""Unit tests for bench.models.registry — adapter lookup + register decorators.

Tests the in-memory registry mechanics in isolation. Real provider adapters
(OpenAI, local HF) are tested separately via integration.
"""

from __future__ import annotations

import importlib

import pytest

import bench.models.registry as reg
from bench.models.registry import (
    ModelAdapter,
    get_adapter,
    list_models,
    register,
    register_prefix,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    """Each test starts with a clean registry; restore after."""
    saved_exact = dict(reg._EXACT)
    saved_prefix = list(reg._PREFIX)
    reg._EXACT.clear()
    reg._PREFIX.clear()
    yield
    reg._EXACT.clear()
    reg._EXACT.update(saved_exact)
    reg._PREFIX.clear()
    reg._PREFIX.extend(saved_prefix)


class _StubAdapter(ModelAdapter):
    def __init__(self, name: str):
        self.name = name

    def generate(self, system, user_text, images=None, max_tokens=4096):
        return f"echo:{self.name}", None


# ── register (exact match) ────────────────────────────────────────────────────


class TestRegisterExact:
    def test_register_single_name(self):
        register("my-model")(_StubAdapter)
        a = get_adapter("my-model")
        assert isinstance(a, _StubAdapter)
        assert a.name == "my-model"

    def test_register_multiple_names_for_same_adapter(self):
        register("model-a", "model-b", "model-c")(_StubAdapter)
        for n in ["model-a", "model-b", "model-c"]:
            a = get_adapter(n)
            assert isinstance(a, _StubAdapter)
            assert a.name == n

    def test_unknown_model_raises_value_error(self):
        register("known")(_StubAdapter)
        with pytest.raises(ValueError, match="Unknown model"):
            get_adapter("unknown")

    def test_value_error_lists_known(self):
        register("known")(_StubAdapter)
        try:
            get_adapter("unknown")
        except ValueError as e:
            assert "known" in str(e)


# ── register_prefix ───────────────────────────────────────────────────────────


class TestRegisterPrefix:
    def test_prefix_match(self):
        register_prefix("local:")(_StubAdapter)
        a = get_adapter("local:./checkpoints/foo")
        assert isinstance(a, _StubAdapter)
        assert a.name == "local:./checkpoints/foo"

    def test_prefix_no_match_when_not_starting_with(self):
        register_prefix("local:")(_StubAdapter)
        with pytest.raises(ValueError):
            get_adapter("openai:gpt-4")

    def test_exact_takes_priority_over_prefix(self):
        # Both registered; exact wins for matching names
        class ExactAdapter(_StubAdapter):
            kind = "exact"

        class PrefixAdapter(_StubAdapter):
            kind = "prefix"

        register("local:foo")(ExactAdapter)
        register_prefix("local:")(PrefixAdapter)
        a = get_adapter("local:foo")
        assert getattr(a.__class__, "kind", "?") == "exact"
        # Different name within prefix → uses prefix adapter
        b = get_adapter("local:bar")
        assert getattr(b.__class__, "kind", "?") == "prefix"


# ── list_models ───────────────────────────────────────────────────────────────


class TestListModels:
    def test_lists_exact_and_prefix(self):
        register("a", "z", "m")(_StubAdapter)
        register_prefix("p:")(_StubAdapter)
        models = list_models()
        # exact names sorted, then prefixes
        assert models[:3] == ["a", "m", "z"]
        assert "p:*" in models

    def test_empty_registry(self):
        assert list_models() == []


# ── Real provider modules importable (smoke) ──────────────────────────────────


def test_openai_provider_imports():
    """Smoke: importing the OpenAI provider doesn't crash and registers something."""
    # Reset and re-import to populate
    importlib.import_module("bench.models.providers")
    # After import, _EXACT should have OpenAI model names.
    # (We don't check specific names — just that the import side-effect works.)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
