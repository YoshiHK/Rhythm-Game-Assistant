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


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
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

def build_marketplace_event(
    *,
    event_type: str,
    provenance_id: str,
    event_id: Optional[str] = None,
    timestamp: Optional[str] = None,
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
    extra_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a marketplace_event aligned with marketplace_events.schema.json
    """
    normalized_provenance_id = _require_str("provenance_id", provenance_id)
    normalized_event_type = _require_str("event_type", event_type)
    normalized_timestamp = _norm_str(timestamp) or _now_iso()

    content = None
    if content_id:
        content = {
            "content_id": _norm_str(content_id),
            "content_type": _norm_str(content_type),
            "version": _norm_str(content_version),
        }
        content = {k: v for k, v in content.items() if v is not None}

    interaction = None
    if action or rating is not None:
        interaction = {
            "action": _norm_str(action),
            "rating": _norm_float(rating),
        }
        interaction = {k: v for k, v in interaction.items() if v is not None}

    transaction = None
    if amount is not None or currency or transaction_type:
        transaction = {
            "amount": _norm_float(amount),
            "currency": _norm_str(currency),
            "type": _norm_str(transaction_type),
        }
        transaction = {k: v for k, v in transaction.items() if v is not None}

    normalized_event_id = _norm_str(event_id) or _make_event_id(
        "mkt",
        f"{normalized_provenance_id}:{normalized_event_type}:{normalized_timestamp}:{_norm_str(content_id)}:{_norm_str(player_id)}"
    )

    event = {
        "event_id": normalized_event_id,
        "event_type": normalized_event_type,
        "timestamp": normalized_timestamp,
        "provenance_id": normalized_provenance_id,
        "player_id": _norm_str(player_id),
        "creator_id": _norm_str(creator_id),
        "content": content,
        "interaction": interaction,
        "transaction": transaction,
    }

    if extra_context:
        event["metrics"] = extra_context

    return {k: v for k, v in event.items() if v is not None}


__all__ = ["build_marketplace_event"]