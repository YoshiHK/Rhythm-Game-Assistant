from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _norm_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Builder (Thin, non-semantic)
# -----------------------------------------------------------------------------

def build_feedback_event(
    *,
    event_type: str,
    source_type: str,
    provenance_id: str,
    player_id: Optional[str] = None,
    session_id: Optional[str] = None,
    game_id: Optional[str] = None,
    song_id: Optional[str] = None,
    recommendation_set_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    rank: Optional[int] = None,
    locale: Optional[str] = None,
    surface: Optional[str] = None,
    mode: Optional[str] = None,
    action: Optional[str] = None,
    reaction_type: Optional[str] = None,
    completion_status: Optional[str] = None,
    dismiss_reason: Optional[str] = None,
    duration_ms: Optional[float] = None,
    retry_count: Optional[int] = None,
    selector_used: Optional[str] = None,
    fallback_triggered: Optional[bool] = None,
    degraded_mode: Optional[bool] = None,
    execution_stage: Optional[str] = None,
    error_code: Optional[str] = None,
    experiment_id: Optional[str] = None,
    variant: Optional[str] = None,
    client_version: Optional[str] = None,
    platform: Optional[str] = None,
    ingestion_source: Optional[str] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build feedback_event aligned with feedback_events.schema.json

    Design guarantees:
    - NO interpretation
    - NO scoring
    - NO reasoning
    - raw payload only
    """

    context = {
        "player_id": _norm_str(player_id),
        "session_id": _norm_str(session_id),
        "game_id": _norm_str(game_id),
        "song_id": _norm_str(song_id),
        "recommendation_set_id": _norm_str(recommendation_set_id),
        "difficulty": _norm_str(difficulty),
        "rank": _norm_int(rank),
        "locale": _norm_str(locale),
        "surface": _norm_str(surface),
        "mode": _norm_str(mode),
    }

    payload = {
        "action": _norm_str(action),
        "reaction_type": _norm_str(reaction_type),
        "completion_status": _norm_str(completion_status),
        "dismiss_reason": _norm_str(dismiss_reason),
        "duration_ms": duration_ms,
        "retry_count": _norm_int(retry_count),
    }

    if extra_payload:
        payload.update(extra_payload)

    system_context = {
        "selector_used": _norm_str(selector_used),
        "fallback_triggered": fallback_triggered,
        "degraded_mode": degraded_mode,
        "execution_stage": _norm_str(execution_stage),
        "error_code": _norm_str(error_code),
    }

    experiment = None
    if experiment_id or variant:
        experiment = {
            "experiment_id": _norm_str(experiment_id),
            "variant": _norm_str(variant),
        }

    ingestion_metadata = {
        "client_version": _norm_str(client_version),
        "platform": _norm_str(platform),
        "ingestion_source": _norm_str(ingestion_source),
    }

    event = {
        "event_id": f"fb_{hash(str(provenance_id) + str(_now_iso()))}",
        "provenance_id": _norm_str(provenance_id),
        "event_type": event_type,
        "source_type": source_type,
        "timestamp": _now_iso(),
        "context": {k: v for k, v in context.items() if v is not None},
        "payload": {k: v for k, v in payload.items() if v is not None},
        "system_context": {k: v for k, v in system_context.items() if v is not None},
        "experiment": experiment,
        "ingestion_metadata": {k: v for k, v in ingestion_metadata.items() if v is not None},
    }

    return {k: v for k, v in event.items() if v is not None}


__all__ = ["build_feedback_event"]