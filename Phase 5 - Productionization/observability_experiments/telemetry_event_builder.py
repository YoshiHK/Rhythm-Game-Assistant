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


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
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
# Builder
# -----------------------------------------------------------------------------

def build_telemetry_event(
    *,
    event_type: str,
    provenance_id: str,
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    player_id: Optional[str] = None,
    session_id: Optional[str] = None,
    game_id: Optional[str] = None,
    song_id: Optional[str] = None,
    recommendation_set_id: Optional[str] = None,
    rank: Optional[int] = None,
    difficulty: Optional[str] = None,
    surface: Optional[str] = None,
    mode: Optional[str] = None,
    locale: Optional[str] = None,
    latency_ms: Optional[float] = None,
    execution_time_ms: Optional[float] = None,
    retry_count: Optional[int] = None,
    success: Optional[bool] = None,
    cost: Optional[float] = None,
    selector_used: Optional[str] = None,
    fallback_triggered: Optional[bool] = None,
    model_version: Optional[str] = None,
    feature_version: Optional[str] = None,
    experiment_id: Optional[str] = None,
    variant: Optional[str] = None,
    error_code: Optional[str] = None,
    error_stage: Optional[str] = None,
    error_message: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build telemetry_event aligned with telemetry_events.schema.json
    """
    normalized_provenance_id = _require_str("provenance_id", provenance_id)
    normalized_event_type = _require_str("event_type", event_type)
    normalized_timestamp = _norm_str(timestamp) or _now_iso()

    context = {
        "game_id": _norm_str(game_id),
        "song_id": _norm_str(song_id),
        "recommendation_set_id": _norm_str(recommendation_set_id),
        "rank": _norm_int(rank),
        "difficulty": _norm_str(difficulty),
        "surface": _norm_str(surface),
        "mode": _norm_str(mode),
        "locale": _norm_str(locale),
    }

    metrics = {
        "latency_ms": _norm_float(latency_ms),
        "execution_time_ms": _norm_float(execution_time_ms),
        "retry_count": _norm_int(retry_count),
        "success": _norm_bool(success),
        "cost": _norm_float(cost),
    }

    decision = {
        "selector_used": _norm_str(selector_used),
        "fallback_triggered": _norm_bool(fallback_triggered),
        "model_version": _norm_str(model_version),
        "feature_version": _norm_str(feature_version),
    }

    experiment = None
    if experiment_id or variant:
        experiment = {
            "experiment_id": _norm_str(experiment_id),
            "variant": _norm_str(variant),
            "exposed": True,
        }

    error = None
    if error_code or error_stage or error_message:
        error = {
            "error_code": _norm_str(error_code),
            "stage": _norm_str(error_stage),
            "message": _norm_str(error_message),
        }

    context = {k: v for k, v in context.items() if v is not None}
    if extra_context:
        context.update(extra_context)

    normalized_event_id = _norm_str(event_id) or _make_event_id(
        "tel",
        f"{normalized_provenance_id}:{normalized_event_type}:{normalized_timestamp}"
    )

    event = {
        "event_id": normalized_event_id,
        "event_type": normalized_event_type,
        "timestamp": normalized_timestamp,
        "provenance_id": normalized_provenance_id,
        "player_id": _norm_str(player_id),
        "session_id": _norm_str(session_id),
        "context": context,
        "metrics": {k: v for k, v in metrics.items() if v is not None},
        "decision": {k: v for k, v in decision.items() if v is not None},
        "experiment": experiment,
        "error": error,
    }

    return {k: v for k, v in event.items() if v is not None}
    
__all__ = ["build_telemetry_event"]    