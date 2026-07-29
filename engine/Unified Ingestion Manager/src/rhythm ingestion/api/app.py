"""
app.py

Responsibilities:
- Initialize FastAPI application
- Wire Phase 6 API routes
- Inject orchestrator and optional Phase 7 / Phase 4 / Phase 4.5 components
- Enforce routing boundaries (no direct phase imports at runtime)

Non-goals:
- No recommendation logic
- No learning logic
- No phase mutation
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# Phase 6 Routing Surface (single source)
# ------------------------------------------------------------
from .recommend import (
    router as recommend_router,
    set_orchestrator,
    set_games_recommender,
    set_personalization_engine,
    set_localization_engine,
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
    personalization_engine=None,
    localization_engine=None,
) -> FastAPI:
    """
    Application factory.
    """

    app = FastAPI()

    # --------------------------------------------------------
    # CORS / preflight handling for browser clients that call
    # the /v1/mcp (or /api/v1/*) surface. This ensures the
    # Authorization header and OPTIONS preflight are accepted.
    # Change allow_origins to specific origins in production.
    # --------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # change to exact origins for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # ----------------------------------------
    # Inject core dependencies (Phase 6 wiring)
    # ----------------------------------------

    set_orchestrator(orchestrator)

    if games_recommender is not None:
        set_games_recommender(games_recommender)

    if personalization_engine is not None:
        set_personalization_engine(personalization_engine)

    if localization_engine is not None:
        set_localization_engine(localization_engine)

    # ----------------------------------------
    # Register routers (single source)
    # ----------------------------------------

    app.include_router(recommend_router)
    app.include_router(auth_router)

    return app
