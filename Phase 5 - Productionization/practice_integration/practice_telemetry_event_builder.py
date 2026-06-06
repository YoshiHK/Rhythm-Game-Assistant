from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


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


def build_practice_telemetry_event(
    *,
    event_type: str,
    provenance_id: str,
    mode: str,
    player_id: Optional[str] = None,
    session_id: Optional[str] = None,
    game_id: Optional[str] = None,
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    section_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    retry_count: Optional[int] = None,
    experiment_id: Optional[str] = None,
    variant: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    extra_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build practice telemetry events aligned with practice_telemetry.schema.json.
    """

    practice_context: Dict[str, Any] = {
        "mode": _norm_str(mode),
        "game_id": _norm_str(game_id),
        "song_id": _norm_str(song_id),
        "difficulty": _norm_str(difficulty),
        "section_id": _norm_str(section_id),
    }
    if extra_context:
        practice_context.update(extra_context)

    metrics: Dict[str, Any] = {
        "duration_ms": _norm_float(duration_ms),
        "retry_count": _norm_int(retry_count),
    }
    if extra_metrics:
        metrics.update(extra_metrics)

    experiment = None
    if experiment_id or variant:
        experiment = {
            "experiment_id": _norm_str(experiment_id),
            "variant": _norm_str(variant),
        }

    obj = {
        "event_id": f"practice_{hash(str(provenance_id) + str(mode) + str(_now_iso()))}",
        "event_type": _norm_str(event_type),
        "timestamp": _now_iso(),
        "provenance_id": _norm_str(provenance_id),
        "player_id": _norm_str(player_id),
        "session_id": _norm_str(session_id),
        "practice_context": {k: v for k, v in practice_context.items() if v is not None},
        "metrics": {k: v for k, v in metrics.items() if v is not None},
        "experiment": experiment,
    }

    return {k: v for k, v in obj.items() if v is not None}


__all__ = ["build_practice_telemetry_event"]