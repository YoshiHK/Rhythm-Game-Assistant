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


def _norm_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _norm_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Builder
# -----------------------------------------------------------------------------

def build_marketplace_event(
    *,
    event_type: str,
    player_id: Optional[str] = None,
    creator_id: Optional[str] = None,
    content_id: Optional[str] = None,
    content_type: Optional[str] = None,
    content_version: Optional[str] = None,
    action: Optional[str] = None,
    rating: Optional[float] = None,
    amount: Optional[float] = None,
    currency: Optional[str] = None,
    transaction_type: Optional[str] = None,
    provenance_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a marketplace_event aligned with marketplace_events.schema.json
    """

    content = None
    if content_id:
        content = {
            "content_id": _norm_str(content_id),
            "content_type": _norm_str(content_type),
            "version": _norm_str(content_version),
        }

    interaction = None
    if action or rating is not None:
        interaction = {
            "action": _norm_str(action),
            "rating": _norm_float(rating),
        }

    transaction = None
    if amount is not None:
        transaction = {
            "amount": _norm_float(amount),
            "currency": _norm_str(currency),
            "type": _norm_str(transaction_type),
        }

    event = {
        "event_id": f"mkt_{hash(str(content_id) + str(player_id) + str(_now_iso()))}",
        "event_type": event_type,
        "timestamp": _now_iso(),
        "provenance_id": _norm_str(provenance_id),
        "player_id": _norm_str(player_id),
        "creator_id": _norm_str(creator_id),
        "content": content,
        "interaction": interaction,
        "transaction": transaction,
    }

    if extra_context:
        event["metrics"] = extra_context

    # remove None fields
    return {k: v for k, v in event.items() if v is not None}


__all__ = ["build_marketplace_event"]