"""
recommend.py
Phase-safe recommendation API entrypoint.

Phase alignment:
- Phase 6: External trigger surface (auth, trigger envelope, observability hooks).
- Phase 5: Read-only response assembly (no learning / no mutation).
- Phase 3+: Execution is invoked ONLY via orchestrator_ext.bridge (OrchestratorBridge).
- Phase 7 (optional): Games recommendation may be wired in via injection (no imports).

Non-negotiable:
- No runtime version switching.
- No direct imports of Phase 1/2/4/5/6/7 logic here (wiring only).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import auth_header, require_softr_bearer

# ✅ The ONLY allowed execution dependency
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge


router = APIRouter(prefix="/api/v1", tags=["recommend"])

# Optional backwards-compatibility router (can be removed later)
_proseka_router = APIRouter(prefix="/api/v1/proseka", tags=["proseka"])


# ------------------------------------------------------------
# Helpers (Phase 6)
# ------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _phase6_trigger_envelope(*, source: str = "softr", surface: str = "recommend_api") -> Dict[str, Any]:
    return {
        "trigger_id": str(uuid4()),
        "source": source,
        "timestamp": _utc_now_iso(),
        "surface": surface,
    }


# ------------------------------------------------------------
# Song Catalog (read-only contract)
# ------------------------------------------------------------

class SongCatalog(Protocol):
    """Read-only catalog produced by Phase 3 (or loaded from a stable store)."""

    def list_song_ids(self, *, game_id: str) -> List[str]: ...
    def chart_ref(self, *, game_id: str, song_id: str) -> Optional[str]: ...
    def metadata(self, *, game_id: str, song_id: str) -> Dict[str, Any]: ...


class InMemorySongCatalog:
    """
    Minimal in-memory catalog for development / tests.

    Expected shape:
    {
      "<game_id>": {
         "<song_id>": {
            "chart_ref": "...path-or-ref...",
            "title": "...",
            ... any extra metadata ...
         },
         ...
      }
    }
    """

    def __init__(self, catalog: Optional[Dict[str, Any]] = None):
        self._catalog: Dict[str, Any] = dict(catalog or {})

    def list_song_ids(self, *, game_id: str) -> List[str]:
        node = self._catalog.get(str(game_id), {})
        if not isinstance(node, dict):
            return []
        return sorted([str(k) for k in node.keys()])

    def chart_ref(self, *, game_id: str, song_id: str) -> Optional[str]:
        node = self._catalog.get(str(game_id), {})
        if not isinstance(node, dict):
            return None
        entry = node.get(str(song_id))
        if not isinstance(entry, dict):
            return None
        ref = entry.get("chart_ref")
        return str(ref) if isinstance(ref, str) and ref.strip() else None

    def metadata(self, *, game_id: str, song_id: str) -> Dict[str, Any]:
        node = self._catalog.get(str(game_id), {})
        if not isinstance(node, dict):
            return {}
        entry = node.get(str(song_id))
        return dict(entry) if isinstance(entry, dict) else {}


SONG_CATALOG: SongCatalog = InMemorySongCatalog()


def set_song_catalog(cat: SongCatalog) -> None:
    global SONG_CATALOG
    SONG_CATALOG = cat


# ------------------------------------------------------------
# Orchestrator wiring (injected)
# ------------------------------------------------------------

_ORCHESTRATOR: Optional[OrchestratorBridge] = None


def set_orchestrator(orch: OrchestratorBridge) -> None:
    """Application startup hook."""
    global _ORCHESTRATOR
    _ORCHESTRATOR = orch


def _get_orchestrator() -> OrchestratorBridge:
    if _ORCHESTRATOR is None:
        raise RuntimeError("OrchestratorBridge not configured")
    return _ORCHESTRATOR


# ------------------------------------------------------------
# Optional injected recommenders (no imports)
# ------------------------------------------------------------

class GamesRecommender(Protocol):
    def recommend_games(
        self,
        *,
        player_id: str,
        locale: str,
        max_items: int,
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        trigger: Dict[str, Any],
    ) -> List[Dict[str, Any]]: ...


_GAMES_RECOMMENDER: Optional[GamesRecommender] = None


def set_games_recommender(rec: GamesRecommender) -> None:
    global _GAMES_RECOMMENDER
    _GAMES_RECOMMENDER = rec


# ------------------------------------------------------------
# API models (Phase-safe)
# ------------------------------------------------------------

class UserInfo(BaseModel):
    user_id: str = Field(..., description="Opaque user id from Softr")
    email: Optional[str] = Field(None, description="User email from Softr (optional)")


class PlayerSignals(BaseModel):
    # Keep numeric inputs as optional strings to avoid Softr JSON issues.
    expert_ap_count: Optional[str] = None
    expert_fc_count: Optional[str] = None
    master_ap_count: Optional[str] = None
    master_fc_count: Optional[str] = None
    expert_clear_rate: Optional[str] = None
    master_clear_rate: Optional[str] = None
    highest_confirmed_difficulty: Optional[str] = "Expert"


class Preferences(BaseModel):
    variant: Optional[str] = "expert"
    allow_personalization: bool = True


class Evidence(BaseModel):
    screenshot_url: Optional[str] = ""
    notes: Optional[str] = ""


class RecommendRequest(BaseModel):
    """
    Unified request envelope.
    - game_id is required and drives downstream routing.
    - mode selects song-level vs game-level recommendation.
    """

    request_id: Optional[str] = None
    source: str = "softr_workflow"

    game_id: str
    locale: str = "zh-HK"
    max_items: int = Field(5, ge=1, le=20)

    # Mode:
    # - "songs": return song recommendations with tips payload (if available)
    # - "games": return game discovery recommendations (Phase 7; optional injection)
    mode: str = "songs"

    # Optional list of songs the client wants tips for (stable, explicit).
    song_ids: Optional[List[str]] = None

    user: Optional[UserInfo] = None
    player_signals: PlayerSignals = Field(default_factory=PlayerSignals)
    preferences: Preferences = Field(default_factory=Preferences)
    evidence: Evidence = Field(default_factory=Evidence)

    # Client metadata (non-semantic)
    client: Dict[str, Any] = Field(default_factory=dict)


class RecommendItem(BaseModel):
    # Unified item shape (song or game)
    item_id: str
    kind: str  # "song" | "game"
    title: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    tips_payload: Optional[Dict[str, Any]] = None
    rationale: Dict[str, Any] = Field(default_factory=dict)


class RecommendResponse(BaseModel):
    request_id: str
    response_id: str
    provenance_id: str
    trigger: Dict[str, Any]
    items: List[RecommendItem]


# ------------------------------------------------------------
# Internal execution helpers
# ------------------------------------------------------------

def _stable_request_id(req: RecommendRequest, trigger: Dict[str, Any]) -> str:
    # Prefer caller-provided request_id; else use trigger_id.
    rid = (req.request_id or "").strip()
    return rid or str(trigger.get("trigger_id") or uuid4())


def _run_tips_for_song(
    *,
    orch: OrchestratorBridge,
    game_id: str,
    song_id: str,
    locale: str,
    chart_ref: str,
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute Phase 3+ pipeline via OrchestratorBridge (the only execution dependency).
    This function is intentionally defensive: it returns diagnostics instead of raising.
    """
    try:
        # We keep kwargs minimal and phase-safe.
        # OrchestratorBridge wraps underlying orchestrator and accepts **kwargs.
        return orch.run(
            game_id=game_id,
            chart_path=chart_ref,
            mode="full",
            locale=locale,
            trigger=trigger,
            song_id=song_id,
        )
    except Exception as e:
        return {"diagnostics": {"error": str(e), "song_id": song_id, "chart_ref": chart_ref}}


def _extract_tips_payload(run_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of tips payload.
    The orchestrator output shape may evolve; this stays defensive.
    """
    if not isinstance(run_result, dict):
        return None

    # Common candidate keys (keep loose; do not assume)
    for key in ("tips_output", "tips", "output", "result"):
        val = run_result.get(key)
        if isinstance(val, dict):
            return val

    # Sometimes tips are nested
    nested = run_result.get("payload")
    if isinstance(nested, dict):
        for key in ("tips_output", "tips"):
            val = nested.get(key)
            if isinstance(val, dict):
                return val

    return None


# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------

@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest,
    authorization: Optional[str] = Depends(auth_header),
) -> RecommendResponse:
    """
    Unified recommendation endpoint (Phase 6 surface).

    - Auth + trigger envelope (Phase 6)
    - Delegates execution via OrchestratorBridge only (Phase 3+)
    - Optional Phase 7 game recommendations via injected recommender (no imports)
    - Response is phase-safe and read-only
    """
    require_softr_bearer(authorization)

    trigger = _phase6_trigger_envelope(source=req.source, surface="recommend_api")
    request_id = _stable_request_id(req, trigger)

    response_id = str(uuid4())
    provenance_id = str(uuid4())

    items: List[RecommendItem] = []

    mode = (req.mode or "songs").strip().lower()

    # --------------------------
    # Mode: Games recommendations (Phase 7, optional)
    # --------------------------
    if mode == "games":
        if _GAMES_RECOMMENDER is None:
            # Non-blocking: return empty list with diagnostics rationale
            return RecommendResponse(
                request_id=request_id,
                response_id=response_id,
                provenance_id=provenance_id,
                trigger=trigger,
                items=[],
            )

        player_id = req.user.user_id if req.user else ""
        # Build profile/history payloads from envelope (phase-safe, presentation-only)
        player_profile = {
            "signals": req.player_signals.model_dump(),
            "preferences": req.preferences.model_dump(),
            "evidence": req.evidence.model_dump(),
            "client": dict(req.client or {}),
        }
        player_history: Dict[str, Any] = {}  # kept empty unless client supplies later

        recs = _GAMES_RECOMMENDER.recommend_games(
            player_id=player_id,
            locale=req.locale,
            max_items=req.max_items,
            player_profile=player_profile,
            player_history=player_history,
            trigger=trigger,
        )

        for idx, r in enumerate(recs or []):
            if not isinstance(r, dict):
                continue
            gid = str(r.get("game_id", "")).strip()
            if not gid:
                continue
            items.append(
                RecommendItem(
                    item_id=gid,
                    kind="game",
                    title=str(r.get("title") or r.get("display_name") or "") or None,
                    payload=dict(r.get("payload") or {}),
                    tips_payload=None,
                    rationale=dict(r.get("rationale") or {"rank": idx + 1}),
                )
            )

        return RecommendResponse(
            request_id=request_id,
            response_id=response_id,
            provenance_id=provenance_id,
            trigger=trigger,
            items=items[: req.max_items],
        )

    # --------------------------
    # Default Mode: Song recommendations (tips)
    # --------------------------
    orch = _get_orchestrator()

    # Determine which songs to process:
    if req.song_ids:
        song_ids = [str(s) for s in req.song_ids if s is not None and str(s).strip()]
        rationale_base = {"source": "request:song_ids"}
    else:
        # Stable default: use catalog order (sorted)
        song_ids = SONG_CATALOG.list_song_ids(game_id=req.game_id)
        rationale_base = {"source": "catalog:default_order"}

    # Produce items up to max_items
    for song_id in song_ids:
        if len(items) >= req.max_items:
            break

        meta = SONG_CATALOG.metadata(game_id=req.game_id, song_id=song_id) or {}
        title = meta.get("title")
        title = str(title) if isinstance(title, str) and title.strip() else None

        chart_ref = SONG_CATALOG.chart_ref(game_id=req.game_id, song_id=song_id)
        if not chart_ref:
            items.append(
                RecommendItem(
                    item_id=song_id,
                    kind="song",
                    title=title,
                    payload={"metadata": meta},
                    tips_payload=None,
                    rationale={**rationale_base, "skip": "no_chart_ref"},
                )
            )
            continue

        run_result = _run_tips_for_song(
            orch=orch,
            game_id=req.game_id,
            song_id=song_id,
            locale=req.locale,
            chart_ref=chart_ref,
            trigger=trigger,
        )

        tips_payload = _extract_tips_payload(run_result)

        items.append(
            RecommendItem(
                item_id=song_id,
                kind="song",
                title=title,
                payload={
                    "metadata": meta,
                    "chart_ref": chart_ref,
                },
                tips_payload=tips_payload,
                rationale={
                    **rationale_base,
                    "executed": True,
                    "diagnostics": dict(run_result.get("diagnostics") or {}) if isinstance(run_result, dict) else {},
                },
            )
        )

    return RecommendResponse(
        request_id=request_id,
        response_id=response_id,
        provenance_id=provenance_id,
        trigger=trigger,
        items=items,
    )


# ------------------------------------------------------------
# Backwards-compatible alias (optional)
# ------------------------------------------------------------

@_proseka_router.post("/recommend", response_model=RecommendResponse)
def proseka_recommend_alias(
    req: RecommendRequest,
    authorization: Optional[str] = Depends(auth_header),
) -> RecommendResponse:
    """
    Compatibility alias for legacy clients that used /api/v1/proseka/recommend.

    This endpoint enforces game_id='proseka' and delegates to /api/v1/recommend.
    Safe to remove once clients migrate.
    """
    # Force proseka routing (compat only)
    req.game_id = "proseka"
    return recommend(req=req, authorization=authorization)


# Expose compatibility router for app.py to include if desired
compat_routers: List[APIRouter] = [_proseka_router]