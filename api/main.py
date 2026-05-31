"""
main.py

ASGI entrypoint for Rhythm Game Assistant API (Phase 6 surface)

Responsibilities:
- Instantiate FastAPI app via application factory
- Inject OrchestratorBridge (Phase 3+ execution layer)
- Keep all wiring external (no business logic here)

This file enables:
    uvicorn main:app --reload
"""

from rhythm_ingestion.api.app import create_app
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge


# -----------------------------------------------------------------------------
# Dependency Injection (Phase-safe)
# -----------------------------------------------------------------------------

# ✅ OrchestratorBridge = ONLY execution dependency allowed by recommend.py
orch = OrchestratorBridge()


# -----------------------------------------------------------------------------
# FastAPI App (factory)
# -----------------------------------------------------------------------------

app = create_app(
    orchestrator=orch,
    games_recommender=None,   # Phase 7 optional (keep None for now)
)