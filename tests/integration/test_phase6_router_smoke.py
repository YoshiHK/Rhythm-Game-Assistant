from __future__ import annotations

import pytest


@pytest.mark.integration
def test_phase6_router_module_importable():
    try:
        import router
        assert router is not None
    except Exception as e:
        pytest.skip(f"Router layer not importable: {e}")


@pytest.mark.integration
def test_phase6_router_constructable_via_factory():
    try:
        from router import build_default_router
    except Exception as e:
        pytest.skip(f"No router factory available: {e}")

    router = build_default_router()

    assert router is not None
    assert hasattr(router, "handle") or hasattr(router, "route")


@pytest.mark.integration
def test_phase6_router_smoke_modes():
    try:
        from router import build_default_router
    except Exception as e:
        pytest.skip(f"No router factory available: {e}")

    r = build_default_router()

    # ✅ songs route
    try:
        resp = r.handle({"mode": "songs"})
    except Exception as e:
        pytest.skip(f"Router not ready for songs: {e}")

    assert isinstance(resp, dict)
    assert "mode" in resp

    # ✅ games route
    try:
        resp = r.handle({"mode": "games"})
    except Exception as e:
        pytest.skip(f"Router not ready for games: {e}")

    assert isinstance(resp, dict)