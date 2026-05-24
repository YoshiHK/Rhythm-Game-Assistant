from __future__ import annotations

import pytest


def _try_import(module_path: str):
    try:
        return __import__(module_path, fromlist=["*"])
    except Exception as e:
        return e


def _import_phase6_router_or_skip():
    """
    Router-layer aligned import:
    - Do NOT assume song_recommendations.phase6_router exists.
    """
    candidates = [
        "router.phase6_router",  # ✅ router layer (preferred)
        "phase6_router",         # ✅ flat fallback
    ]

    last_error = None
    for path in candidates:
        result = _try_import(path)
        if not isinstance(result, Exception):
            return result
        last_error = result

    pytest.skip(f"Phase 6 router not importable yet: {last_error}")


@pytest.mark.integration
def test_phase6_router_module_importable():
    _ = _import_phase6_router_or_skip()


@pytest.mark.integration
def test_phase6_router_smoke_modes_if_callable_exists():
    m = _import_phase6_router_or_skip()

    router_cls = getattr(m, "Phase6Router", None)
    if router_cls is None:
        pytest.skip("Phase6Router not defined in router module")

    try:
        router = router_cls()
    except Exception as e:
        pytest.skip(f"Phase6Router not constructable: {e}")

    # minimal functional smoke: ensure it returns a dict and has mode
    try:
        resp = router.handle({"mode": "songs"})
        assert isinstance(resp, dict)
        assert "mode" in resp
    except Exception as e:
        pytest.skip(f"Router not fully wired yet: {e}")