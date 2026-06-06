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


def build_recommendation_request(
    *,
    request_id: str,
    player_id: str,
    request_type: str,
    provenance_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    game_id: Optional[str] = None,
    locale: Optional[str] = None,
    player_level: Optional[str] = None,
    recent_activity: Optional[str] = None,
    capability_tier: Optional[str] = None,
    recommended_focus: Optional[str] = None,
    experiment_id: Optional[str] = None,
    variant: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    extra_personalization: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build recommendation request objects aligned with recommendation_request.schema.json.

    Schema requirements:
    - request_id, player_id, timestamp, request_type: required
    - context.game_id: required
    - experiment: optional, additionalProperties: false
    """

    context: Dict[str, Any] = {
        "game_id": _norm_str(game_id),
        "locale": _norm_str(locale),
        "player_level": _norm_str(player_level),
        "recent_activity": _norm_str(recent_activity),
    }
    if extra_context:
        context.update(extra_context)

    personalization: Dict[str, Any] = {
        "capability_tier": _norm_str(capability_tier),
        "recommended_focus": _norm_str(recommended_focus),
    }
    if extra_personalization:
        personalization.update(extra_personalization)

    experiment = None
    if experiment_id or variant:
        experiment = {
            "experiment_id": _norm_str(experiment_id),
            "variant": _norm_str(variant),
        }
        experiment = {k: v for k, v in experiment.items() if v is not None}

    obj = {
        "request_id": _norm_str(request_id),
        "player_id": _norm_str(player_id),
        "provenance_id": _norm_str(provenance_id),
        "timestamp": timestamp or _now_iso(),
        "request_type": _norm_str(request_type),
        "context": {k: v for k, v in context.items() if v is not None},
        "personalization": {k: v for k, v in personalization.items() if v is not None},
        "experiment": experiment,
    }

    return {k: v for k, v in obj.items() if v is not None}


__all__ = ["build_recommendation_request"]
