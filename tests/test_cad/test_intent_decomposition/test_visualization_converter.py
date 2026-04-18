"""Tests for SVG-to-PNG converter detection and DYLD handling."""

import os
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def clean_env(monkeypatch):
    """Ensure DYLD_FALLBACK_LIBRARY_PATH is not set."""
    monkeypatch.delenv("DYLD_FALLBACK_LIBRARY_PATH", raising=False)


@pytest.fixture
def mock_darwin(monkeypatch):
    """Mock macOS platform."""
    monkeypatch.setattr(sys, "platform", "darwin")


@pytest.fixture
def mock_linux(monkeypatch):
    """Mock Linux platform."""
    monkeypatch.setattr(sys, "platform", "linux")


def test_check_converter_oserror_returns_none(monkeypatch, clean_env, mock_darwin):
    """OSError from cairosvg import should be caught and return None."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Mock all CLI converters as unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError("converter not found")

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg import to raise OSError (native lib not found)
    def mock_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise OSError("no library called 'libcairo' was found")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Mock Homebrew paths exist
    monkeypatch.setattr(
        os.path, "exists", lambda p: p in ["/opt/homebrew/lib", "/usr/local/lib"]
    )

    result = check_svg_to_png_converter()

    # Should return None gracefully, not raise
    assert result is None


def test_check_converter_import_error_returns_none(monkeypatch, clean_env, mock_darwin):
    """ImportError from cairosvg import should be caught and return None."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Mock all CLI converters as unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError("converter not found")

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg not installed
    def mock_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise ImportError("No module named 'cairosvg'")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)

    monkeypatch.setattr(os.path, "exists", lambda p: p == "/opt/homebrew/lib")

    result = check_svg_to_png_converter()

    assert result is None


def test_check_converter_cairosvg_available(monkeypatch, clean_env, mock_darwin):
    """Successful cairosvg import should return 'cairosvg'."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Mock all CLI converters as unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError("converter not found")

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg available
    mock_cairosvg = MagicMock()
    monkeypatch.setitem(sys.modules, "cairosvg", mock_cairosvg)
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/opt/homebrew/lib")

    result = check_svg_to_png_converter()

    assert result == "cairosvg"


def test_dyld_restored_after_failed_import(monkeypatch, clean_env, mock_darwin):
    """DYLD_FALLBACK_LIBRARY_PATH should be restored after failed cairosvg import."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Set initial value
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/original/path"
    original_value = os.environ["DYLD_FALLBACK_LIBRARY_PATH"]

    # Mock CLI converters unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg import fails
    def mock_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise ImportError("No module named 'cairosvg'")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/opt/homebrew/lib")

    result = check_svg_to_png_converter()

    # Should restore original value
    assert os.environ["DYLD_FALLBACK_LIBRARY_PATH"] == original_value
    assert result is None


def test_dyld_removed_if_was_unset(monkeypatch, clean_env, mock_darwin):
    """DYLD_FALLBACK_LIBRARY_PATH should be removed if it wasn't set originally."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Ensure not set
    assert "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ

    # Mock CLI converters unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg import fails
    def mock_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise OSError("libcairo not found")
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/opt/homebrew/lib")

    result = check_svg_to_png_converter()

    # Should be removed (not left as empty string)
    assert "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ
    assert result is None


def test_dyld_not_set_on_non_darwin(monkeypatch, clean_env, mock_linux):
    """DYLD should not be touched on non-macOS platforms."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Mock CLI converters unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg unavailable
    def mock_import(name, *args, **kwargs):
        if name == "cairosvg":
            raise ImportError()
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)

    result = check_svg_to_png_converter()

    # DYLD should never be set on Linux
    assert "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ
    assert result is None


def test_dyld_no_trailing_colon(monkeypatch, clean_env, mock_darwin):
    """DYLD value should not have trailing colon when original is unset."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    captured_dyld = None

    # Mock CLI converters unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg import to capture DYLD value
    def mock_import(name, *args, **kwargs):
        nonlocal captured_dyld
        if name == "cairosvg":
            captured_dyld = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH")
            raise ImportError()  # Fail after capturing
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/opt/homebrew/lib")

    check_svg_to_png_converter()

    # Verify no trailing colon
    assert captured_dyld is not None
    assert not captured_dyld.endswith(":")
    assert captured_dyld == "/opt/homebrew/lib"


def test_dyld_intel_and_arm_paths(monkeypatch, clean_env, mock_darwin):
    """Both Intel and Apple Silicon Homebrew paths should be included."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    captured_dyld = None

    # Mock CLI converters unavailable
    def mock_run_fail(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", mock_run_fail)

    # Mock cairosvg import to capture DYLD value
    def mock_import(name, *args, **kwargs):
        nonlocal captured_dyld
        if name == "cairosvg":
            captured_dyld = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH")
            raise ImportError()
        return original_import(name, *args, **kwargs)

    import builtins

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Both paths exist
    def mock_exists(p):
        return p in ["/opt/homebrew/lib", "/usr/local/lib"]

    monkeypatch.setattr(os.path, "exists", mock_exists)

    check_svg_to_png_converter()

    # Both paths should be in DYLD value
    assert captured_dyld is not None
    assert "/opt/homebrew/lib" in captured_dyld
    assert "/usr/local/lib" in captured_dyld
    # Order should be: /opt/homebrew/lib:/usr/local/lib
    assert captured_dyld == "/opt/homebrew/lib:/usr/local/lib"


def test_inkscape_preferred_over_cairosvg(monkeypatch, clean_env):
    """Inkscape should be preferred over cairosvg when both available."""
    from src.cad.intent_decomposition.utils.visualization import (
        check_svg_to_png_converter,
    )

    # Mock inkscape available
    def mock_run_inkscape(args, *a, **kw):
        if args[0] == "inkscape":
            return MagicMock(returncode=0)
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", mock_run_inkscape)

    # Mock cairosvg also available
    mock_cairosvg = MagicMock()
    monkeypatch.setitem(sys.modules, "cairosvg", mock_cairosvg)

    result = check_svg_to_png_converter()

    # Should return inkscape, not cairosvg
    assert result == "inkscape"
