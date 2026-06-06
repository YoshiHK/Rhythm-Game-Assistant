from __future__ import annotations

import hashlib
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
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _norm_bool(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    return None


def _require_str(name: str, value: Any) -> str:
    s = _norm_str(value)
    if not s:
        raise ValueError(f"{name} is required")
    return s


def _make_event_id(prefix: str, key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


# -----------------------------------------------------------------------------
# Builder (Thin, non-semantic)
# -----------------------------------------------------------------------------

def build_feedback_event(
    *,
    event_type: str,
    source_type: str,
    provenance_id: str,
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
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
    normalized_provenance_id = _require_str("provenance_id", provenance_id)
    normalized_event_type = _require_str("event_type", event_type)
    normalized_source_type = _require_str("source_type", source_type)
    normalized_timestamp = _norm_str(timestamp) or _now_iso()

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

    payload = {k: v for k, v in payload.items() if v is not None}
    if not payload:
        payload = {}

    system_context = {
        "selector_used": _norm_str(selector_used),
        "fallback_triggered": _norm_bool(fallback_triggered),
        "degraded_mode": _norm_bool(degraded_mode),
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

    normalized_event_id = _norm_str(event_id) or _make_event_id(
        "fb",
        f"{normalized_provenance_id}:{normalized_event_type}:{normalized_source_type}:{normalized_timestamp}"
    )

    event = {
        "event_id": normalized_event_id,
        "provenance_id": normalized_provenance_id,
        "event_type": normalized_event_type,
        "source_type": normalized_source_type,
        "timestamp": normalized_timestamp,
        "context": {k: v for k, v in context.items() if v is not None},
        "payload": payload,
        "system_context": {k: v for k, v in system_context.items() if v is not None},
        "experiment": experiment,
        "ingestion_metadata": {k: v for k, v in ingestion_metadata.items() if v is not None},
    }

    return {k: v for k, v in event.items() if v is not None}


__all__ = ["build_feedback_event"]