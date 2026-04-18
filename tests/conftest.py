"""Root pytest configuration for cadance tests.

Provides shared fixtures and utilities, including CadQuery compatibility checks.
"""

import pytest


def _cadquery_works() -> bool:
    """Check if cadquery actually works (not just imports).

    CadQuery may import successfully but fail at runtime due to OCP version
    incompatibilities (e.g., HashCode attribute removed in newer versions).
    This smoke test catches those runtime failures.
    """
    try:
        import cadquery as cq

        # Smoke test - actually create geometry
        box = cq.Workplane("XY").box(1, 1, 1)
        # Access faces to trigger HashCode if broken
        _ = box.faces().vals()
        return True
    except Exception:
        return False


CADQUERY_WORKS = _cadquery_works()

requires_working_cadquery = pytest.mark.skipif(
    not CADQUERY_WORKS,
    reason="CadQuery not available or OCP incompatible",
)
