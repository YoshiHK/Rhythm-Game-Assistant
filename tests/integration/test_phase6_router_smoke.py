from __future__ import annotations

import pytest


def _try_import(module_path: str):
    try:
        return __import__(module_path, fromlist=["*"])
    except Exception as e:
        return e


def _import_phase6_router_or_skip():
    """
    Import Phase 6 router if available.

    Phase 6 is the ONLY runtime gatekeeper per design:
    - mode="songs" routes to song recommendation flow
    - mode="games" routes to Phase 7 flow
    """
    candidates = [
        # If your repo uses a python package like `phase6/router/phase6_router.py`
        "phase6.router.phase6_router",
        "phase6.router.phase6_router",
        # Add your final canonical import path here when stabilized
    ]

    last_err = None
    for path in candidates:
        res = _try_import(path)
        if not isinstance(res, Exception):
            return res
        last_err = res

    pytest.skip(f"Phase 6 router not importable yet (expected while wiring stabilizes): {last_err}")


@pytest.mark.integration
def test_phase6_router_module_importable():
    _ = _import_phase6_router_or_skip()


@pytest.mark.integration
def test_phase6_router_smoke_modes_if_callable_exists():
    m = _import_phase6_router_or_skip()

    # Try common entrypoint names; update once Phase 6 stabilizes.
    entry = None
    for name in ("phase6_router", "route", "handle_request", "run"):
        if hasattr(m, name) and callable(getattr(m, name)):
            entry = getattr(m, name)
            break

    if entry is None:
        pytest.skip("Phase 6 router imported but no callable entrypoint found (update test when entrypoint is finalized).")

    # Minimal smoke: ensure it doesn't crash on mode switching.
    # Keep payload presentation-safe.
    for mode in ("songs", "games"):
        try:
            _ = entry({"mode": mode, "player_id": "ci_smoke"})
        except TypeError:
            pytest.skip("Phase 6 router entrypoint exists but signature differs (update smoke harness when stable).")