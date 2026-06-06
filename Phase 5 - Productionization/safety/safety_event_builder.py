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


# -----------------------------------------------------------------------------
# Severity Mapping (Contract-aligned)
# -----------------------------------------------------------------------------

def _derive_severity(score: Optional[float]) -> str:
    """
    Convert detection score into severity level.
    """
    if score is None:
        return "low"

    if score >= 0.9:
        return "critical"
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


# -----------------------------------------------------------------------------
# Builder
# -----------------------------------------------------------------------------

def build_safety_event(
    *,
    event_type: str,
    player_id: Optional[str] = None,
    provenance_id: Optional[str] = None,
    signal: Optional[Dict[str, Any]] = None,
    risk_score: Optional[float] = None,
    action: str = "none",
    require_review: bool = False,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build safety_event aligned with safety_events.schema.json
    """

    severity = _derive_severity(risk_score)

    event = {
        "event_id": f"safety_{hash(str(player_id) + str(_now_iso()))}",
        "event_type": event_type,
        "timestamp": _now_iso(),
        "severity": severity,
        "provenance_id": _norm_str(provenance_id),
        "player_id": _norm_str(player_id),
        "signal": signal,
        "decision": {
            "action": action,
            "automated": True,
        },
        "review": {
            "required": bool(require_review),
            "status": "pending" if require_review else "resolved",
        },
    }

    if extra_context:
        event["context"] = extra_context

    # remove None fields
    return {k: v for k, v in event.items() if v is not None}


__all__ = ["build_safety_event"]