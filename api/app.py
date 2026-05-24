"""
app.py

Responsibilities:
- Initialize FastAPI application
- Wire Phase 6 API routes
- Inject orchestrator and optional Phase 7 components
- Enforce routing boundaries (no direct phase imports at runtime)

Non-goals:
- No recommendation logic
- No learning logic
- No phase mutation
"""

from __future__ import annotations

from fastapi import FastAPI

# ------------------------------------------------------------
# Phase 6 Routing Surface (single source)
# ------------------------------------------------------------
from .recommend import (
    router as recommend_router,
    set_orchestrator,
    set_games_recommender,
)

# Auth routes (Phase 6 owned)
from .auth import router as auth_router


# ------------------------------------------------------------
# Application Factory
# ------------------------------------------------------------
def create_app(
    *,
    orchestrator,
    games_recommender=None,
) -> FastAPI:
    """
    Application factory.

    All runtime dependencies must be injected explicitly.
    No implicit initialization is allowed.
    """

    app = FastAPI()

    # --------------------------------------------------------
    # Inject core execution dependency (required)
    # --------------------------------------------------------
    set_orchestrator(orchestrator)

    # --------------------------------------------------------
    # Inject optional Phase 7 recommender
    # --------------------------------------------------------
    if games_recommender is not None:
        set_games_recommender(games_recommender)

    # --------------------------------------------------------
    # Register routes (Phase 6 surface only)
    # --------------------------------------------------------
    app.include_router(recommend_router)
    app.include_router(auth_router)

    return app