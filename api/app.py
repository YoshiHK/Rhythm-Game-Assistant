"""
app.py

Responsibilities:
- Initialize FastAPI application
- Wire Phase 6 API routes
- Inject orchestrator and optional Phase 7 components
- Enforce routing boundaries (no direct phase imports)

Non-goals:
- No recommendation logic
- No learning logic
- No phase mutation
"""

from __future__ import annotations

from fastapi import FastAPI

# ------------------------------------------------------------
# Core API routers (Phase 6 surface)
# ------------------------------------------------------------

from .recommend import (
    router as recommend_router,
    compat_routers as recommend_compat_routers,
    set_orchestrator,
    set_games_recommender,
)

# Auth routes (Phase 6 owned)
from .auth import router as auth_router

# ------------------------------------------------------------
# Runtime wiring (injected from platform / main)
# ------------------------------------------------------------

def create_app(
    *,
    orchestrator,
    games_recommender=None,
) -> FastAPI:
    """
    Application factory.

    Parameters:
    - orchestrator:
        OrchestratorBridge (required)
        The ONLY execution dependency (Phase 3+)

    - games_recommender:
        Optional callable implementing Phase 7 game discovery.
        Injected here to avoid importing Phase 7 modules directly.
    """
    app = FastAPI(
        title="Rhythm Game Assistant API",
        version="0.1.0",
    )

    # -------------------------
    # Inject runtime dependencies
    # -------------------------

    # Phase 3+ execution bridge (mandatory)
    set_orchestrator(orchestrator)

    # Phase 7 game recommendations (optional)
    if games_recommender is not None:
        set_games_recommender(games_recommender)

    # -------------------------
    # Register API routes
    # -------------------------

    # Auth (Phase 6)
    app.include_router(auth_router)

    # Unified recommendation API
    app.include_router(recommend_router)

    # Optional backward-compatible routes
    for r in recommend_compat_routers:
        app.include_router(r)

    return app
