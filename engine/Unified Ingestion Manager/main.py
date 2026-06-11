from __future__ import annotations

from fastapi import FastAPI

from api import create_app

# ✅ Runtime components
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge
from rhythm_ingestion.runtime_meta import RuntimeMetaManager


# -----------------------------------------------------------------------------
# Runtime Builder
# -----------------------------------------------------------------------------
def build_runtime_components():
    runtime_meta = RuntimeMetaManager()

    orchestrator = OrchestratorBridge()

    return {
        "orchestrator": orchestrator,
        "runtime_meta": runtime_meta,
        "games_recommender": None,  # plug later
        "personalization_engine": None,
        "localization_engine": None,
    }


# -----------------------------------------------------------------------------
# App creation
# -----------------------------------------------------------------------------
runtime = build_runtime_components()

app = create_app(
    orchestrator=runtime["orchestrator"],
    games_recommender=runtime["games_recommender"],
    personalization_engine=runtime["personalization_engine"],
    localization_engine=runtime["localization_engine"],
)

# ✅ Inject runtime_meta into app state
app.state.runtime_meta = runtime["runtime_meta"]