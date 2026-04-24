"""Model adapter registry — plug-and-play LLM backends.

A runner only knows `--model <name>`; everything provider-specific lives
inside an Adapter. To add a new model, drop a `register(...)` line in a
new providers/<x>.py and import it from providers/__init__.py.

Adapter contract (single method):

    generate(system, user_text, images=None, max_tokens=4096) -> (text, err)

`text` is None on failure and `err` is a short string. Images is a list of
PIL.Image.Image (the adapter handles encoding).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class ModelAdapter(ABC):
    """Provider-agnostic LLM client. Concrete subclass per provider."""

    name: str

    @abstractmethod
    def generate(
        self,
        system: str,
        user_text: str,
        images: list | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str | None, str | None]:
        """Returns (response_text, error_string). text=None on failure."""


# ── Registry ──────────────────────────────────────────────────────────────────

# Exact-match: model_name → adapter factory(name) -> ModelAdapter
_EXACT: dict[str, Callable[[str], ModelAdapter]] = {}
# Prefix match: prefix → adapter factory(name) -> ModelAdapter
_PREFIX: list[tuple[str, Callable[[str], ModelAdapter]]] = []


def register(*names: str):
    """Decorator: register an adapter class for one or more exact model names."""

    def deco(cls):
        for n in names:
            _EXACT[n] = lambda name, c=cls: c(name)
        return cls

    return deco


def register_prefix(prefix: str):
    """Decorator: register an adapter class for a name prefix (e.g. 'local:')."""

    def deco(cls):
        _PREFIX.append((prefix, lambda name, c=cls: c(name)))
        return cls

    return deco


def get_adapter(model: str) -> ModelAdapter:
    """Return an adapter instance for `model` or raise ValueError."""
    if model in _EXACT:
        return _EXACT[model](model)
    for prefix, factory in _PREFIX:
        if model.startswith(prefix):
            return factory(model)
    known = sorted(_EXACT) + [f"{p}*" for p, _ in _PREFIX]
    raise ValueError(f"Unknown model: {model!r}. Registered: {known}")


def list_models() -> list[str]:
    return sorted(_EXACT) + [f"{p}*" for p, _ in _PREFIX]
