from __future__ import annotations

from typing import Any, Dict

# ---------------------------------------------------------------------
# Event Builders (ENTRY ONLY)
# ---------------------------------------------------------------------

from feedback_aggregation.feedback_event_builder import build_feedback_event
from observability_experiments.telemetry_event_builder import build_telemetry_event
from marketplace.marketplace_event_builder import build_marketplace_event
from safety.safety_event_builder import build_safety_event


# ---------------------------------------------------------------------
# Strict Routing Table
# ---------------------------------------------------------------------

_EVENT_ROUTING = {
    "feedback": build_feedback_event,
    "telemetry": build_telemetry_event,
    "marketplace": build_marketplace_event,
    "safety": build_safety_event,
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _norm_category(x: Any) -> str:
    return str(x).strip().lower() if x is not None else ""


# ---------------------------------------------------------------------
# Public API (STRICT)
# ---------------------------------------------------------------------

def route_event(
    *,
    event_category: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Phase 5 Event Router (STRICT ENTRY LAYER)

    Responsibilities:
    - Route raw payloads into the correct event builder
    - Enforce entry-builder usage
    - Ensure only structured events enter Phase 5 pipelines
    """
    category = _norm_category(event_category)

    if category not in _EVENT_ROUTING:
        raise ValueError(
            f"Unsupported event_category: {event_category}. "
            f"Allowed: {list(_EVENT_ROUTING.keys())}"
        )

    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    builder = _EVENT_ROUTING[category]
    return builder(**payload)


# ---------------------------------------------------------------------
# Optional: Deterministic Inference (SAFE MODE)
# ---------------------------------------------------------------------

def infer_and_route_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infer event type from payload structure.

    Use ONLY if event_category is unavailable.
    Explicit route_event(...) is preferred.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")

    # feedback_event
    if "source_type" in payload:
        return build_feedback_event(**payload)

    # telemetry_event
    telemetry_keys = {
        "latency_ms",
        "execution_time_ms",
        "success",
        "cost",
        "selector_used",
        "model_version",
        "feature_version",
        "error_code",
        "error_stage",
        "error_message",
    }
    if any(k in payload for k in telemetry_keys):
        return build_telemetry_event(**payload)

    # marketplace_event
    marketplace_keys = {
        "creator_id",
        "content_id",
        "content_type",
        "content_version",
        "transaction_type",
        "currency",
        "amount",
        "rating",
    }
    if any(k in payload for k in marketplace_keys):
        return build_marketplace_event(**payload)

    # safety_event
    safety_keys = {
        "risk_score",
        "signal",
        "require_review",
    }
    if any(k in payload for k in safety_keys):
        return build_safety_event(**payload)

    raise ValueError("Unable to infer event type from payload")


__all__ = [
    "route_event",
    "infer_and_route_event",
]