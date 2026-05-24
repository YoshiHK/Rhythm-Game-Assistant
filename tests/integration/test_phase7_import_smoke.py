from __future__ import annotations

import pytest


@pytest.mark.integration
def test_phase7_modules_importable():
    # Phase 7 root should be on PYTHONPATH in CI.
    modules = ("registry", "ranking", "explanation", "feedback", "observability", "catalog")
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            raise AssertionError(f"Phase 7 module '{mod}' not importable: {e}")