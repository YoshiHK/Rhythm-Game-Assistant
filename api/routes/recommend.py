"""
recommend.py
Phase-safe recommendation API entrypoint.

Phase alignment (authoritative intent):
- Phase 6: External trigger surface (auth, trigger envelope, observability hooks).
- Phase 5: Read-only response assembly (no learning / no mutation).
- Phase 3+: Execution is invoked ONLY via orchestrator_ext.bridge (OrchestratorBridge).
- Phase 7 (optional): Games recommendation may be wired in via injection (no imports).

Non-negotiable (authoritative intent):
- No runtime version switching.
- No direct imports of Phase 1/2/4/5/6/7 logic here (wiring only).

Routing discipline:
- No backward-compatibility guarantees; deprecated paths are removed (not archived).
- This module exposes a single Phase 6 surface: POST /api/v1/recommend
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import auth_header, require_softr_bearer

# ✅ The ONLY allowed execution dependency
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge


# -----------------------------------------------------------------------------
# Router (single source)
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/api/v1", tags=["recommend"])


# -----------------------------------------------------------------------------
# Helpers (Phase 6)
# -----------------------------------------------------------------------------
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _phase6_trigger_envelope(*, source: str = "softr", surface: str = "recommend_api") -> Dict[str, Any]:
    return {
        "trigger_id": str(uuid4()),
        "source": source,
        "timestamp": _utc_now_iso(),
        "surface": surface,
    }


def _stable_request_id(req: "RecommendRequest", trigger: Dict[str, Any]) -> str:
    rid = (req.request_id or "").strip()
    return rid or str(trigger.get("trigger_id") or uuid4())


# -----------------------------------------------------------------------------
# Song Catalog (read-only contract; injection only)
# -----------------------------------------------------------------------------
class SongCatalog(Protocol):
    """Read-only catalog produced by Phase 3 (or loaded from a stable store)."""
    # Keep protocol minimal. Implementations may provide one of:
    # def get_chart_ref(self, game_id: str, song_id: str) -> str: ...
    # def chart_ref_for(self, game_id: str, song_id: str) -> str: ...


_SONG_CATALOG: Optional[SongCatalog] = None


def set_song_catalog(cat: SongCatalog) -> None:
    """Startup hook: inject a read-only catalog implementation."""
    global _SONG_CATALOG
    _SONG_CATALOG = cat


def _resolve_chart_ref(*, game_id: str, song_id: str) -> str:
    """
    Resolve chart reference safely.

    Priority:
      1) Injected SongCatalog (if present and provides a compatible method)
      2) Deterministic fallback: charts/<game_id>/<song_id>.json

    This supports 'short-circuit loop protection': explicit song_ids always win.
    """
    cat = _SONG_CATALOG
    if cat is not None:
        for attr in ("get_chart_ref", "chart_ref_for", "chart_ref", "resolve_chart_ref"):
            fn = getattr(cat, attr, None)
            if callable(fn):
                try:
                    ref = fn(game_id, song_id)
                    if isinstance(ref, str) and ref.strip():
                        return ref
                except Exception:
                    # Do not let catalog issues break the Phase 6 surface
                    break

    return f"charts/{game_id}/{song_id}.json"


# -----------------------------------------------------------------------------
# Orchestrator wiring (injected)
# -----------------------------------------------------------------------------
_ORCHESTRATOR: Optional[OrchestratorBridge] = None


def set_orchestrator(orch: OrchestratorBridge) -> None:
    """Startup hook: configure the only execution dependency."""
    global _ORCHESTRATOR
    _ORCHESTRATOR = orch


def _get_orchestrator() -> OrchestratorBridge:
    if _ORCHESTRATOR is None:
        raise RuntimeError("OrchestratorBridge not configured")
    return _ORCHESTRATOR


# -----------------------------------------------------------------------------
# Optional injected recommenders (no imports)
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# API models (Phase-safe)
# -----------------------------------------------------------------------------
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
    request_id: Optional[str] = Field(None, description="Optional caller-provided stable request id")
    mode: str = Field("song", description="'song' or 'game'")
    game_id: str = Field(..., description="Game identifier, e.g. 'proseka'")
    locale: str = Field("en-US", description="BCP-47 locale, e.g. 'zh-HK'")

    user: Optional[UserInfo] = None

    # Short-circuit loop protection: explicit song_ids override any catalog enumeration.
    song_ids: List[str] = Field(default_factory=list, description="Explicit song ids to evaluate")

    player_signals: PlayerSignals = Field(default_factory=PlayerSignals)
    preferences: Preferences = Field(default_factory=Preferences)
    evidence: Evidence = Field(default_factory=Evidence)

    # Optional, phase-safe bags for injected recommenders
    player_profile: Dict[str, Any] = Field(default_factory=dict)
    player_history: Dict[str, Any] = Field(default_factory=dict)

    max_items: int = Field(1, ge=1, le=25, description="Maximum items to return")


class RecommendItem(BaseModel):
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


# -----------------------------------------------------------------------------
# Internal execution helpers (defensive)
# -----------------------------------------------------------------------------
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
    Defensive: return diagnostics instead of raising.
    """
    try:
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
    Best-effort extraction of tips payload. Output shape may evolve; stay defensive.
    """
    if not isinstance(run_result, dict):
        return None

    for path in (
        ("tips_payload",),
        ("result", "tips_payload"),
        ("payload", "tips_payload"),
        ("tips",),
    ):
        cur: Any = run_result
        ok = True
        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and isinstance(cur, dict):
            return cur

    return None


# -----------------------------------------------------------------------------
# Endpoint (single source)
# -----------------------------------------------------------------------------
@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest,
    authorization: Optional[str] = Depends(auth_header),
) -> RecommendResponse:
    """
    Unified recommendation endpoint (Phase 6 surface).
    """

    # Phase 6 security boundary
    require_softr_bearer(authorization)

    trigger = _phase6_trigger_envelope(source="softr", surface="recommend_api")
    request_id = _stable_request_id(req, trigger)

    response_id = str(uuid4())
    provenance_id = str(uuid4())

    mode = (req.mode or "song").strip().lower()

    # -----------------------------
    # GAME recommendation (optional injection)
    # -----------------------------
    if mode == "game":
        if _GAMES_RECOMMENDER is None:
            raise HTTPException(status_code=501, detail="Games recommender not configured")

        player_id = (req.user.user_id if req.user else "").strip() or "anonymous"
        recs = _GAMES_RECOMMENDER.recommend_games(
            player_id=player_id,
            locale=req.locale,
            max_items=req.max_items,
            player_profile=req.player_profile,
            player_history=req.player_history,
            trigger=trigger,
        )

        items: List[RecommendItem] = []
        for r in recs[: req.max_items]:
            item_id = str(r.get("item_id") or r.get("game_id") or "")
            if not item_id:
                continue
            items.append(
                RecommendItem(
                    item_id=item_id,
                    kind="game",
                    title=r.get("title"),
                    payload={k: v for k, v in r.items() if k not in ("title",)},
                    rationale=r.get("rationale") or {},
                )
            )

        return RecommendResponse(
            request_id=request_id,
            response_id=response_id,
            provenance_id=provenance_id,
            trigger=trigger,
            items=items,
        )

    # -----------------------------
    # SONG recommendation (default)
    # -----------------------------
    song_ids = list(req.song_ids or [])

    # Short-circuit loop protection:
    # If explicit song_ids are not provided, do NOT enumerate a full catalog here.
    if not song_ids:
        return RecommendResponse(
            request_id=request_id,
            response_id=response_id,
            provenance_id=provenance_id,
            trigger=trigger,
            items=[],
        )

    try:
        orch = _get_orchestrator()
    except RuntimeError as e:
        # Endpoint-level friendliness while still enforcing configuration
        raise HTTPException(status_code=503, detail=str(e))

    items: List[RecommendItem] = []

    for song_id in song_ids[: req.max_items]:
        chart_ref = _resolve_chart_ref(game_id=req.game_id, song_id=song_id)
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
                payload={
                    "game_id": req.game_id,
                    "chart_ref": chart_ref,
                    "diagnostics": run_result.get("diagnostics") if isinstance(run_result, dict) else None,
                },
                tips_payload=tips_payload,
                rationale={"source": "orchestrator", "short_circuit": True},
            )
        )

    return RecommendResponse(
        request_id=request_id,
        response_id=response_id,
        provenance_id=provenance_id,
        trigger=trigger,
        items=items,
    )