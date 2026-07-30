from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from api import create_app

# ✅ Runtime components
from rhythm_ingestion.orchestrator import ingest
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge
from rhythm_ingestion.runtime_meta import RuntimeMetaManager


class Phase3IngestCore:
    """
    Wiring adapter only.

    Purpose:
    - adapts Phase 3 ingest(...) into the .run(...) surface expected by OrchestratorBridge
    - does not modify Phase 1–7 logic
    - does not change canonical_row, pattern/tag logic, tips generation,
      personalization, or localization
    """

    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        chart = Path(chart_path)

        # If chart_path is a file, Phase 3 ingest works from its parent folder.
        # If chart_path is already a directory-like reference, use it directly.
        source_dir = str(chart.parent if chart.suffix else chart)

        return ingest(
            source_dir=source_dir,
            db_path=kwargs.get("db_path"),
            dry_run=bool(kwargs.get("dry_run", True)),
            only_game=game_id,
            json_out=kwargs.get("json_out"),
            tips_mode=kwargs.get("tips_mode", mode),
            scan_state_path=kwargs.get("scan_state_path"),
            chart_asset_db=kwargs.get("chart_asset_db"),
            skip_known_assets=bool(kwargs.get("skip_known_assets", True)),
            **{
                k: v
                for k, v in kwargs.items()
                if k
                not in {
                    "db_path",
                    "dry_run",
                    "json_out",
                    "tips_mode",
                    "scan_state_path",
                    "chart_asset_db",
                    "skip_known_assets",
                }
            },
        )

    def recommend(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Placeholder wiring surface.

        Real player-first recommendation should be wired to the Phase 5–7
        recommender later. This method exists only so the API does not fail
        because the Phase 3 ingestion core is chart/run-oriented.
        """
        return {
            "ok": False,
            "reason": "games_recommender_not_configured",
            "message": (
                "Phase3IngestCore supports chart-first .run(...). "
                "Player-first .recommend(...) should be wired to the Phase 5–7 recommender."
            ),
            "items": [],
        }


# -----------------------------------------------------------------------------
# Runtime Builder
# -----------------------------------------------------------------------------
def build_runtime_components():
    runtime_meta = RuntimeMetaManager()

    core = Phase3IngestCore()
    orchestrator = OrchestratorBridge(_core=core)

    return {
        "orchestrator": orchestrator,
        "runtime_meta": runtime_meta,
        "games_recommender": None,
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