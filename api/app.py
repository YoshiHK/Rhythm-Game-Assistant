from __future__ import annotations

from fastapi import FastAPI

from .routes.proseka import router as proseka_router


def create_app() -> FastAPI:
    app = FastAPI(
        title='Rhythm Game Assistant API (Thin Layer)',
        version='0.1.0',
        description=(
            'Thin backend API layer intended for Softr integration. '            'This layer is wiring-only and must not modify completed-phase semantics.'
        ),
    )

    app.include_router(proseka_router)

    @app.get('/health')
    def health():
        return {'ok': True}

    return app


app = create_app()
