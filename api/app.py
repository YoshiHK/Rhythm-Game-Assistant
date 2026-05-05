from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.proseka import router as proseka_router
from .routes.recommend import router as recommend_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Rhythm Game Assistant API (Thin Layer)",
        version="0.1.0",
        description=(
            "Thin backend API layer intended for Softr integration. "
            "This layer is wiring-only and must not modify completed-phase semantics."
        ),
    )

    # Phase-6 wiring: allow Softr browser origin to call this API through ngrok.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://*.softr.app",
            "https://beatblast-laverna57427.softr.app",
        ],
        allow_credentials=False,
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(proseka_router)
    app.include_router(recommend_router)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()