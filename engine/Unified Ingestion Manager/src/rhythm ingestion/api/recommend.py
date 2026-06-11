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
from typing import Any, Dict, List, Optional, Protocol, Literal
from uuid import uuid4

from fastapi import Request
from pydantic import BaseModel, Field

from .auth import auth_header, require_softr_bearer

# ✅ ONLY execution boundary
from rhythm_ingestion.orchestrator_ext.bridge import OrchestratorBridge

# ✅ TEMP cache (read-only, may move later)
_CROSS_GAME_GOLDEN_CACHE: Optional[Dict[str, Any]] = None

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
        """Must be pure (no mutation). Should not perform network I/O."""    
            fn = getattr(cat, attr, None)
            if callable(fn):
                try:
                    ref = fn(game_id, song_id)
                    if isinstance(ref, str) and ref.strip():
                        return ref
                except Exception:
                    # do not break full fallback chain
                    continue


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
# Optional injected personalization / localization engines (no direct imports)
# -----------------------------------------------------------------------------
class PersonalizationEngine(Protocol):
    def build_personalization(
        self,
        *,
        locale: str,
        player_signals: Dict[str, Any],
        preferences: Dict[str, Any],
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        trigger: Dict[str, Any],
    ) -> Dict[str, Any]: ...

    def personalize_song(
        self,
        *,
        game_id: str,
        song_id: str,
        locale: str,
        player_signals: Dict[str, Any],
        preferences: Dict[str, Any],
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        trigger: Dict[str, Any],
    ) -> Dict[str, Any]: ...

    def personalize_game(
        self,
        *,
        game_id: str,
        locale: str,
        player_signals: Dict[str, Any],
        preferences: Dict[str, Any],
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        trigger: Dict[str, Any],
        item: Dict[str, Any],
    ) -> Dict[str, Any]: ...
    
_PERSONALIZATION_ENGINE: Optional[PersonalizationEngine] = None


class LocalizationEngine(Protocol):
    def build_localization(
        self,
        *,
        locale: str,
        trigger: Dict[str, Any],
        personalization: Dict[str, Any],
    ) -> Dict[str, Any]: ...

    def localize_item(
        self,
        *,
        locale: str,
        kind: str,
        title: Optional[str],
        payload: Dict[str, Any],
        tips_payload: Optional[Dict[str, Any]],
        rationale: Dict[str, Any],
        trigger: Dict[str, Any],
    ) -> Dict[str, Any]: ...

_LOCALIZATION_ENGINE: Optional[LocalizationEngine] = None


def set_personalization_engine(engine: PersonalizationEngine) -> None:
    global _PERSONALIZATION_ENGINE
    _PERSONALIZATION_ENGINE = engine


def set_localization_engine(engine: LocalizationEngine) -> None:
    global _LOCALIZATION_ENGINE
    _LOCALIZATION_ENGINE = engine


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
    
    mode: Literal["song", "game"] = Field(
        "song",
        description="'song' or 'game'"
    )

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
def _load_cross_game_golden_snapshots() -> Dict[str, Any]:
    global _CROSS_GAME_GOLDEN_CACHE
    if _CROSS_GAME_GOLDEN_CACHE is not None:
        return _CROSS_GAME_GOLDEN_CACHE

    here = Path(__file__).resolve()

    def _safe_parent(path: Path, idx: int) -> Optional[Path]:
        try:
            return path.parents[idx]
        except IndexError:
            return None

    candidates = [
        here.parent / "cross_game_golden_snapshots.json",
        here.parent.parent / "cross_game_golden_snapshots.json",
    ]

    root2 = _safe_parent(here, 2)

    if root2 is not None:
        candidates.extend([
            root2 / "cross_game_golden_snapshots.json",
            root2 / "config" / "cross_game_golden_snapshots.json",
            root2 / "data" / "cross_game_golden_snapshots.json",
        ])

    for path in candidates:
        try:
            if path.exists():
                _CROSS_GAME_GOLDEN_CACHE = json.loads(path.read_text(encoding="utf-8"))
                return _CROSS_GAME_GOLDEN_CACHE
        except Exception:
            continue

    _CROSS_GAME_GOLDEN_CACHE = {}
    return _CROSS_GAME_GOLDEN_CACHE

def _game_registry_key(game_id: Optional[str]) -> str:
    """
    Normalize API/game ids to snapshot registry keys.

    NOTE:
    - This alias map is a suggested compatibility layer.
    - The attached snapshot currently shows 'ユメステ' but not a separate 'yumesute' key.
    """
    gid = _game_id_value(game_id)

    aliases = {
        "yumesute": "ユメステ",  # suggested alias because snapshot shows ユメステ
    }

    return aliases.get(gid, gid)


def _cross_game_profile(game_id: Optional[str]) -> Dict[str, Any]:
    registry = _load_cross_game_golden_snapshots()
    gid = _game_registry_key(game_id)

    profile = registry.get(gid)
    if isinstance(profile, dict):
        return profile

    return {
        "difficulty_tiers": ["generic"],
        "completion_ladder": ["clear"],
    }


def _cross_game_progress_snapshot(req: RecommendRequest) -> Dict[str, Any]:
    """
    Suggested canonical location for normalized player progress by tier/state.

    Expected shape (proposal):
    {
        "expert": {"clear": 200, "fc": 80, "ap": 10},
        "master": {"clear": 120, "fc": 30, "ap": 2}
    }
    """
    profile = _player_profile_dict(req)
    history = _player_history_dict(req)

    snap = profile.get("cross_game_progress")
    if isinstance(snap, dict):
        return snap

    snap = history.get("cross_game_progress")
    if isinstance(snap, dict):
        return snap

    return {}

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
        return {
            "diagnostics": {
                "error": str(e),
                "song_id": song_id,
                "chart_ref": chart_ref,
                "trigger_id": trigger.get("trigger_id"),
            }
        }


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
    
def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default
        
def _player_signals_dict(req: RecommendRequest) -> Dict[str, Any]:
    obj = req.player_signals
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {}
        
def _preferences_dict(req: RecommendRequest) -> Dict[str, Any]:
    obj = req.preferences
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return {}
        
def _player_profile_dict(req: RecommendRequest) -> Dict[str, Any]:
    obj = req.player_profile
    if isinstance(obj, dict):
        return obj
    return {}

def _player_history_dict(req: RecommendRequest) -> Dict[str, Any]:
    obj = req.player_history
    if isinstance(obj, dict):
        return obj
    return {}
    
def _locale_value(locale: Optional[str]) -> str:
    """
    Defensive locale normalization (lightweight).

    Keeps original BCP-47 string but ensures non-null + safe default.
    """
    if not locale or not isinstance(locale, str):
        return "en-US"

    return locale.strip() or "en-US"


def _canonical_locale(locale: Optional[str]) -> str:
    """
    Canonical language mapping (Phase 4.5 core).
    """
    if not locale:
        return "en"

    loc = locale.lower()

    if loc.startswith("en"):
        return "en"
    if loc.startswith("zh"):
        return "zh"
    if loc.startswith("ja"):
        return "ja"
    if loc.startswith("ko"):
        return "ko"

    return "en"


def _game_id_value(game_id: Optional[str]) -> str:
    """
    Defensive normalization for game_id.
    """
    if not game_id or not isinstance(game_id, str):
        return "unknown"

    return (game_id.strip().lower() or "unknown")




def _default_personalization_context(
    req: RecommendRequest,
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Safe fallback personalization (wiring-layer only).
    Snapshot-driven where possible; legacy expert/master fallback otherwise.
    """

    ps = _player_signals_dict(req)
    prefs = _preferences_dict(req)

    game_id = _game_id_value(req.game_id)
    locale = _locale_value(req.locale)

    game_profile = _cross_game_profile(game_id)
    difficulty_tiers = list(game_profile.get("difficulty_tiers") or [])
    completion_ladder = list(game_profile.get("completion_ladder") or [])

    # ------------------------------------------------------
    # 1) Snapshot-driven progress (preferred)
    # ------------------------------------------------------
    progress = _cross_game_progress_snapshot(req)

    snapshot_score = 0.0
    snapshot_rows_present = False

    if isinstance(progress, dict) and progress:
        for tier_index, tier in enumerate(difficulty_tiers, start=1):
            tier_row = progress.get(tier)
            if not isinstance(tier_row, dict):
                continue

            snapshot_rows_present = True

            for state_index, state in enumerate(completion_ladder, start=1):
                value = _to_float(tier_row.get(state))
                snapshot_score += value * tier_index * state_index

    # ------------------------------------------------------
    # # 2) Transitional fallback when snapshot progress is unavailable
    # ------------------------------------------------------
    expert_ap = _to_float(ps.get("expert_ap_count"))
    expert_fc = _to_float(ps.get("expert_fc_count"))
    master_ap = _to_float(ps.get("master_ap_count"))
    master_fc = _to_float(ps.get("master_fc_count"))
    expert_clear = _to_float(ps.get("expert_clear_rate"))
    master_clear = _to_float(ps.get("master_clear_rate"))

    legacy_score = (
        expert_ap * 3.0
        + expert_fc * 2.0
        + master_ap * 4.0
        + master_fc * 3.0
        + expert_clear * 0.25
        + master_clear * 0.35
    )

    signal_score = snapshot_score if snapshot_rows_present else legacy_score

    highest_confirmed = (
        ps.get("highest_confirmed_difficulty")
        or _player_profile_dict(req).get("highest_confirmed_difficulty")
        or (difficulty_tiers[-1] if difficulty_tiers else "generic")
    )

    allow_personalization = bool(prefs.get("allow_personalization", True))
    variant = prefs.get("variant") or "expert"

    if signal_score >= 120:
        capability_tier = "advanced"
        recommended_focus = "top_tier_growth"
    elif signal_score >= 40:
        capability_tier = "intermediate"
        recommended_focus = "consistency_growth"
    else:
        capability_tier = "beginner"
        recommended_focus = "clear_stability"

    return {
        "applied": allow_personalization,
        "capability_tier": capability_tier,
        "recommended_focus": recommended_focus,
        "signal_score": signal_score,
        "highest_confirmed_difficulty": highest_confirmed,
        "variant": variant,

        "decision_source": (
            "recommend_api_snapshot_fallback"
            if snapshot_rows_present
            else "recommend_api_legacy_fallback"
        ),
        "applied_reason": (
            "allowed_by_preferences"
            if allow_personalization
            else "disabled_by_user"
        ),
        "trigger_id": trigger.get("trigger_id"),

        "game_profile": {
            "game_id": game_id,
            "locale": locale,
            "difficulty_tiers": difficulty_tiers,
            "completion_ladder": completion_ladder,
            "snapshot_present": snapshot_rows_present,
            "snapshot_source": "cross_game_golden_snapshots",
        },
    }

def _build_personalization_context(
    req: RecommendRequest,
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    if _PERSONALIZATION_ENGINE is not None:
        if hasattr(_PERSONALIZATION_ENGINE, "build_personalization"):
            try:
                return _PERSONALIZATION_ENGINE.build_personalization(
                    locale=_locale_value(req.locale),
                    player_signals=_player_signals_dict(req),
                    preferences=_preferences_dict(req),
                    player_profile=_player_profile_dict(req),
                    player_history=_player_history_dict(req),
                    trigger=trigger,
                )
            
            except Exception as e:
                fallback = _default_personalization_context(req, trigger)
                fallback["diagnostics"] = {
                    "stage": "build_personalization",
                    "error": str(e),
                    "trigger_id": trigger.get("trigger_id"),
                }
                return fallback



    return _default_personalization_context(req, trigger)


def _default_localization_context(
    locale: str,
    trigger: Dict[str, Any],
    personalization: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Safe fallback localization (wiring-layer only).
    No phase imports. Deterministic. Read-only.
    """

    I18N = {
        "en": {
            "headline": "Your recommendation is ready",
            "tips_label": "Gameplay Tips",
            "recommendation_label": "Recommended Songs",
            "locale_status": "English template applied",
        },
        "zh": {
            "headline": "你的推薦已準備好",
            "tips_label": "遊玩提示",
            "recommendation_label": "推薦歌曲",
            "locale_status": "已套用中文模板",
        },
        "ja": {
            "headline": "おすすめの結果が準備できました",
            "tips_label": "プレイのコツ",
            "recommendation_label": "おすすめ楽曲",
            "locale_status": "日本語テンプレートを適用しました",
        },
        "ko": {
            "headline": "추천 결과가 준비되었습니다",
            "tips_label": "플레이 팁",
            "recommendation_label": "추천 곡",
            "locale_status": "한국어 템플릿이 적용되었습니다",
        },
    }

    canonical = _canonical_locale(locale)
    messages = I18N.get(canonical, I18N["en"])
    requested = _locale_value(locale).lower()
    fallback_used = not requested.startswith(canonical)

    return {
        "messages": messages,
        "meta": {
            "requested_locale": locale,
            "resolved_locale": canonical,
            "fallback_used": fallback_used,
            "translation_source": "recommend_api_fallback",
            "trigger_id": trigger.get("trigger_id"),
            "personalization_capability_tier": personalization.get("capability_tier"),
        },
    }


def _build_localization_context(
    locale: str,
    trigger: Dict[str, Any],
    personalization: Dict[str, Any],
) -> Dict[str, Any]:
    if _LOCALIZATION_ENGINE is not None:
        try:
            return _LOCALIZATION_ENGINE.build_localization(
                locale=_locale_value(locale),
                trigger=trigger,
                personalization=personalization,
            )
        
        
        except Exception as e:
            fallback = _default_localization_context(locale, trigger, personalization)
            fallback_meta = dict(fallback.get("meta") or {})
            fallback_meta.update({
                "error": str(e),
                "fallback": True,
            })
            fallback["meta"] = fallback_meta
            return fallback



    return _default_localization_context(locale, trigger, personalization)

def _apply_personalization_to_song(
    *,
    req: RecommendRequest,
    song_id: str,
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optional personalization layer for song results.
    Never raises; returns empty dict on failure or when engine is absent.
    """
    engine = _PERSONALIZATION_ENGINE
    if engine is None:
        return {}

    try:
        return engine.personalize_song(
            game_id=_game_id_value(req.game_id),
            song_id=song_id,
            locale=_locale_value(req.locale),
            player_signals=_player_signals_dict(req),
            preferences=_preferences_dict(req),
            player_profile=_player_profile_dict(req),
            player_history=_player_history_dict(req),
            trigger=trigger,
        ) or {}

    except Exception as e:        
        return {
            "diagnostics": {
                "stage": "personalize_song",
                "error": str(e),
                "trigger_id": trigger.get("trigger_id"),
                "song_id": song_id,
            }
        }



def _apply_personalization_to_game(
    *,
    req: RecommendRequest,
    item: Dict[str, Any],
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optional personalization layer for game results.
    Never raises; returns empty dict on failure or when engine is absent.
    """
    engine = _PERSONALIZATION_ENGINE
    if engine is None:
        return {}

    try:
        return engine.personalize_game(
            game_id=_game_id_value(req.game_id),
            locale=_locale_value(req.locale),
            player_signals=_player_signals_dict(req),
            preferences=_preferences_dict(req),
            player_profile=_player_profile_dict(req),
            player_history=_player_history_dict(req),
            trigger=trigger,
            item=item,
        ) or {}
    except Exception as e:     
        return {
            "diagnostics": {
                "stage": "personalize_game",
                "error": str(e),
                "trigger_id": trigger.get("trigger_id"),
                "game_id": _game_id_value(req.game_id),
            }
        }



def _apply_localization(
    *,
    req: RecommendRequest,
    kind: str,
    title: Optional[str],
    payload: Dict[str, Any],
    tips_payload: Optional[Dict[str, Any]],
    rationale: Dict[str, Any],
    trigger: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Optional localization layer.
    Never raises. If no engine is configured, return inputs unchanged.
    """
    engine = _LOCALIZATION_ENGINE
    if engine is None:
        return {
            "title": title,
            "payload": payload,
            "tips_payload": tips_payload,
            "rationale": rationale,
        }

    try:
        localized = engine.localize_item(
            locale=_locale_value(req.locale),
            kind=kind,
            title=title,
            payload=payload,
            tips_payload=tips_payload,
            rationale=rationale,
            trigger=trigger,
        ) or {}

        return {
            "title": localized.get("title", title),
            "payload": localized.get("payload") or payload,
            "tips_payload": localized.get("tips_payload", tips_payload),
            "rationale": localized.get("rationale", rationale),
        }

    except Exception as e:
        fallback_rationale = dict(rationale)
        fallback_rationale["localization_error"] = str(e)

        return {
            "title": title,
            "payload": payload,
            "tips_payload": tips_payload,
            "rationale": fallback_rationale,
        }
        
def _build_song_rationale_from_run_result(
    run_result: Dict[str, Any],
    song_id: str,
) -> Dict[str, Any]:
    """
    Normalize reason system (Phase 5 → Phase 6 API).
    """

    if not isinstance(run_result, dict):
        return {
            "reason_codes": ["unknown"],
            "primary_reason": "unknown",
            "source": "fallback",
        }

    items = (
        run_result.get("recommendations", {}).get("items")
        if isinstance(run_result.get("recommendations"), dict)
        else None
    )

    if isinstance(items, list):
        for item in items:
            if item.get("song_name") and str(item.get("song_name")) == str(song_id):
                reason = item.get("reason") or "unknown"

                return {
                    "reason_codes": [reason],
                    "primary_reason": reason,
                    "rank": item.get("rank"),
                    "score": item.get("score"),
                    "source": "metadata_alignment",
                }

    return {
        "reason_codes": ["orchestrator_default"],
        "primary_reason": "orchestrator_default",
        "source": "orchestrator",
    }
    
def _normalize_rationale(raw: Any) -> Dict[str, Any]:
    """
    Unified reasoning normalization for ALL layers.
    Accepts multiple legacy formats.
    """

    if not raw:
        return {
            "reason_codes": ["unknown"],
            "primary_reason": "unknown",
        }

    # ✅ already correct format
    if isinstance(raw, dict) and "reason_codes" in raw:
        return {
            "reason_codes": list(raw.get("reason_codes") or ["unknown"]),
            "primary_reason": raw.get("primary_reason") or (raw.get("reason_codes") or ["unknown"])[0],
            "score": raw.get("score"),
            "rank": raw.get("rank"),
            "source": raw.get("source"),
        }

    # ✅ legacy: single string
    if isinstance(raw, str):
        return {
            "reason_codes": [raw],
            "primary_reason": raw,
        }

    # ✅ legacy: {"reason": "..."}
    if isinstance(raw, dict) and "reason" in raw:
        reason = raw.get("reason")
        return {
            "reason_codes": [reason] if reason else ["unknown"],
            "primary_reason": reason or "unknown",
        }

    return {
        "reason_codes": ["unknown"],
        "primary_reason": "unknown",
    }


# -----------------------------------------------------------------------------
# Endpoint (single source)
# -----------------------------------------------------------------------------
@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest,
    authorization: Optional[str] = Depends(auth_header),
    request: Request = None,
) -> RecommendResponse:
    """
    Unified recommendation endpoint (Phase 6 surface).
    """

    runtime_meta = getattr(request.app.state, "runtime_meta", None)

    # -----------------------------
    # Phase 6 security boundary
    # -----------------------------
    require_softr_bearer(authorization)

    trigger = _phase6_trigger_envelope(source="softr", surface="recommend_api")
    request_id = _stable_request_id(req, trigger)

    response_id = str(uuid4())
    provenance_id = str(uuid4())

    mode = (req.mode or "song").strip().lower()

    # ✅ Start runtime run (API mode)
    if runtime_meta:
        ctx = runtime_meta.start_run(mode="api")
        runtime_meta.current_context = ctx

    # ------------------------------------------------------
    # Request-level context
    # ------------------------------------------------------
    personalization_context = _build_personalization_context(req, trigger)

    localization_context = _build_localization_context(
        req.locale,
        trigger,
        personalization_context,
    )

    # ======================================================
    # GAME mode
    # ======================================================
    if mode == "game":

        if _GAMES_RECOMMENDER is None:
            raise HTTPException(501, "Games recommender not configured")

        player_id = (req.user.user_id if req.user else "").strip() or "anonymous"

        diag = None

        try:
            recs = router.recommend_games(
                player_id=player_id,
                locale=req.locale,
                max_items=req.max_items,
                player_profile=req.player_profile,
                player_history=req.player_history,
                trigger=trigger,
            ) or []
        except Exception as e:
            recs = []
            diag = {
                "stage": "recommend_games",
                "error": str(e),
                "trigger_id": trigger.get("trigger_id"),
            }

        items: List[RecommendItem] = []

        for r in recs[: req.max_items]:
            item_id = str(r.get("item_id") or r.get("game_id") or "")
            if not item_id:
                continue

            payload = {
                **{k: v for k, v in r.items() if k not in ("title",)},
                "personalization_context": personalization_context,
                "localization_context": localization_context,
            }

            if diag:
                payload["diagnostics"] = diag

            overlay = _apply_personalization_to_game(
                req=req,
                item=payload,
                trigger=trigger,
            )

            if overlay:
                payload["personalization"] = overlay

            # ✅ ✅ ✅ UNIFIED reasoning (GAME)
            normalized_rationale = _normalize_rationale(r.get("rationale"))

            localized = _apply_localization(
                req=req,
                kind="game",
                title=r.get("title"),
                payload=payload,
                tips_payload=None,
                rationale=normalized_rationale,
                trigger=trigger,
            )
            
            reason = interpret_feedback(
                trigger=trigger,
                request=req.model_dump() if hasattr(req, "model_dump") else dict(req),
                run_result={"recommendations": {"items": recs}} if isinstance(recs, list) else recs,
                diagnostics=diag,
                tips_payload=None,
                personalization_context=personalization_context,
                localization_context=localization_context,
                provenance_id=provenance_id,
            )

            payload["feedback_reason"] = reason

            items.append(
                RecommendItem(
                    item_id=item_id,
                    kind="game",
                    title=localized.get("title"),
                    payload=localized.get("payload", payload),
                    rationale=localized.get("rationale", normalized_rationale),
                )
            )

        response = RecommendResponse(
            request_id=request_id,
            response_id=response_id,
            provenance_id=provenance_id,
            trigger=trigger,
            items=items,
        )


    # ======================================================
    # SONG mode
    # ======================================================
    else:

        song_ids = list(req.song_ids or [])

        if not song_ids:
            response = RecommendResponse(
                request_id=request_id,
                response_id=response_id,
                provenance_id=provenance_id,
                trigger=trigger,
                items=[],
            )
        else:

            try:
                orch = _get_orchestrator()
            except RuntimeError as e:
                raise HTTPException(503, str(e))

            items: List[RecommendItem] = []

            for song_id in song_ids[: req.max_items]:

                chart_ref = _resolve_chart_ref(
                    game_id=req.game_id,
                    song_id=song_id,
                )

                run_result = _run_tips_for_song(
                    orch=orch,
                    game_id=req.game_id,
                    song_id=song_id,
                    locale=req.locale,
                    chart_ref=chart_ref,
                    trigger=trigger,
                )

                tips_payload = _extract_tips_payload(run_result)

                diagnostics = (
                    run_result.get("diagnostics")
                    if isinstance(run_result, dict)
                    else None
                )

                payload = {
                    "game_id": req.game_id,
                    "chart_ref": chart_ref,
                    "personalization_context": personalization_context,
                    "localization_context": localization_context,
                }

                if diagnostics:
                    payload["diagnostics"] = diagnostics

                overlay = _apply_personalization_to_song(
                    req=req,
                    song_id=song_id,
                    trigger=trigger,
                )

                if overlay:
                    payload["personalization"] = overlay

                # ✅ ✅ ✅ UNIFIED reasoning (SONG)
                rationale = _build_song_rationale_from_run_result(
                    run_result=run_result,
                    song_id=song_id,
                )

                localized = _apply_localization(
                    req=req,
                    kind="song",
                    title=None,
                    payload=payload,
                    tips_payload=tips_payload,
                    rationale=rationale,
                    trigger=trigger,
                )
                               
                reason = interpret_feedback(
                    trigger=trigger,
                    request=req.model_dump() if hasattr(req, "model_dump") else dict(req),
                    run_result=run_result,
                    diagnostics=diagnostics,
                    tips_payload=tips_payload,
                    personalization_context=personalization_context,
                    localization_context=localization_context,
                    provenance_id=provenance_id,
                )
                
                payload["feedback_reason"] = reason
                
                items.append(
                    RecommendItem(
                        item_id=song_id,
                        kind="song",
                        title=localized.get("title"),
                        payload=localized.get("payload", payload),
                        tips_payload=localized.get("tips_payload", tips_payload),
                        rationale=localized.get("rationale", rationale),
                    )
                )

            response = RecommendResponse(
                request_id=request_id,
                response_id=response_id,
                provenance_id=provenance_id,
                trigger=trigger,
                items=items,
            )

    # ✅ Finalize runtime run
    if runtime_meta:
        runtime_meta.finalize_run(
            status="completed",
            extra={
                "mode": mode,
                "items": len(response.items),
                "request_id": request_id,
            },
        )

        # ✅ Safe extraction for Phase7Router result
        game_items = recs.items if (mode == "game" and hasattr(recs, "items")) else []

        runtime_meta.write_json_artifact(
            "game_recommendation_meta",
            {
                "report_type": "game_recommendation_meta",
                "run_id": ctx.run_id,
                "items": [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in game_items
                ],
            }
        )

    return response