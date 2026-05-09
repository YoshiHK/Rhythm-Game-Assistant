"""
recommend.py
Phase-safe recommendation endpoint (Song-level).

Phase alignment:
- Phase 6: External trigger surface (auth, trigger envelope, observability).
- Phase 5: Read-only recommendation response assembly.
- Phase 3: Execution is invoked ONLY via orchestrator_ext.bridge.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal, Protocol
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import auth_header, require_softr_bearer

# ✅ The ONLY allowed execution dependency
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge

router = APIRouter(prefix="/api/v1", tags=["recommend"])


# -----------------------------
# Helpers (Phase 6)
# -----------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _phase6_trigger_envelope(*, source: str = "softr") -> Dict[str, Any]:
    return {
        "trigger_id": str(uuid4()),
        "source": source,
        "timestamp": _utc_now_iso(),
        "surface": "recommend_api",
    }


# -----------------------------
# Song Catalog (read-only contract)
# -----------------------------

class SongCatalog(Protocol):
    """Read-only catalog produced by Phase 3."""
    def list_song_ids(self, *, game_id: str) -> List[str]: ...
    def chart_ref(self, *, game_id: str, song_id: str) -> Optional[str]: ...
    def metadata(self, *, game_id: str, song_id: str) -> Dict[str, Any]: ...


class InMemorySongCatalog:
    """Minimal in-memory catalog for development / tests."""
    def __init__(self, catalog: Optional[Dict[str, Any]] = None):
        self._catalog = dict(catalog or {})

    def list_song_ids(self, *, game_id: str) -> List[str]:
        return list(self._catalog.get(game_id, {}).keys())

    def chart_ref(self, *, game_id: str, song_id: str) -> Optional[str]:
        return self._catalog.get(game_id, {}).get(song_id, {}).get("chart_ref")

    def metadata(self, *, game_id: str, song_id: str) -> Dict[str, Any]:
        return dict(self._catalog.get(game_id, {}).get(song_id, {}))


SONG_CATALOG: SongCatalog = InMemorySongCatalog()


# -----------------------------
# Orchestrator wiring (injected)
# -----------------------------

_ORCHESTRATOR: Optional[OrchestratorBridge] = None


def set_orchestrator(orch: OrchestratorBridge) -> None:
    """Application startup hook."""
    global _ORCHESTRATOR
    _ORCHESTRATOR = orch


def _get_orchestrator() -> OrchestratorBridge:
    if _ORCHESTRATOR is None:
        raise RuntimeError("OrchestratorBridge not configured")
    return _ORCHESTRATOR


# -----------------------------
# API models
# -----------------------------

class RecommendV1Request(BaseModel):
    game_id: str
    locale: str = "zh-HK"
    max_items: int = Field(5, ge=1, le=20)


class RecommendItem(BaseModel):
    song_id: str
    title: Optional[str]
    tips_payload: Optional[Dict[str, Any]]
    rationale: Dict[str, Any]


class RecommendV1Response(BaseModel):
    request_id: str
    response_id: str
    provenance_id: str
    trigger: Dict[str, Any]
    items: List[RecommendItem]


# -----------------------------
# Endpoints
# -----------------------------

@router.post("/recommend", response_model=RecommendV1Response)
def recommend(
    req: RecommendV1Request,
    authorization: Optional[str] = Depends(auth_header),
) -> RecommendV1Response:
    require_softr_bearer(authorization)

    request_id = str(uuid4())
    response_id = str(uuid4())
    provenance_id = str(uuid4())
    trigger = _phase6_trigger_envelope()

    orch = _get_orchestrator()

    song_ids = SONG_CATALOG.list_song_ids(game_id=req.game_id)[: req.max_items]
    items: List[RecommendItem] = []

    for sid in song_ids:
        meta = SONG_CATALOG.metadata(game_id=req.game_id, song_id=sid)
        chart_ref = SONG_CATALOG.chart_ref(game_id=req.game_id, song_id=sid)

        tips_payload = None
        if chart_ref:
            tips_payload = orch.run(
                game_id=req.game_id,
                chart_path=chart_ref,
                mode="tips",
                locale=req.locale,
                provenance_id=provenance_id,
            )

        items.append(
            RecommendItem(
                song_id=sid,
                title=meta.get("title"),
                tips_payload=tips_payload,
                rationale={
                    "type": "catalog_order",
                    "note": "Deterministic placeholder; Phase 5 ranking applies later.",
                },
            )
        )

    return RecommendV1Response(
        request_id=request_id,
        response_id=response_id,
        provenance_id=provenance_id,
        trigger=trigger,
        items=items,
    )