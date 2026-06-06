from __future__ import annotations

from typing import Any, Dict

# ---------------------------------------------------------------------
# ✅ Event Builders (ENTRY ONLY)
# ---------------------------------------------------------------------

# Feedback / Telemetry / Marketplace / Safety are the ONLY entry types
from feedback_aggregation.feedback_event_builder import build_feedback_event
from observability_experiments.telemetry_event_builder import build_telemetry_event
from marketplace.marketplace_event_builder import build_marketplace_event
from safety.safety_event_builder import build_safety_event


# ---------------------------------------------------------------------
# ✅ Strict Routing Table
# ---------------------------------------------------------------------

_EVENT_ROUTING = {
    "feedback": build_feedback_event,
    "telemetry": build_telemetry_event,
    "marketplace": build_marketplace_event,
    "safety": build_safety_event,
}


# ---------------------------------------------------------------------
# ✅ Public API (STRICT)
# ---------------------------------------------------------------------

def route_event(
    *,
    event_category: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Phase 5 Event Router (STRICT ENTRY LAYER)

    Responsibilities:
    - Route raw signals into the correct event builder
    - Enforce event construction discipline
    - Ensure only structured events enter Phase 5 pipelines

    Contract:
    - ALL external ingestion MUST go through this function
    - ONLY entry event types are supported
    """

    if event_category not in _EVENT_ROUTING:
        raise ValueError(
            f"Unsupported event_category: {event_category}. "
            f"Allowed: {list(_EVENT_ROUTING.keys())}"
        )

    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    builder = _EVENT_ROUTING[event_category]

    return builder(**payload)


# ---------------------------------------------------------------------
# ✅ Optional: Deterministic Inference (SAFE MODE)
# ---------------------------------------------------------------------

def infer_and_route_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Infer event type from payload structure.

    Use ONLY when event_category is unavailable.

    This function applies minimal deterministic rules.
    """

    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")

    # ------------------------------------------------------------------
    # Feedback Detection
    # ------------------------------------------------------------------
    if "source_type" in payload:
        return build_feedback_event(**payload)

    # ------------------------------------------------------------------
    # Telemetry Detection
    # ------------------------------------------------------------------
    if "latency_ms" in payload or "execution_time_ms" in payload:
        return build_telemetry_event(**payload)

    if "metrics" in payload and "success" in payload:
        return build_telemetry_event(**payload)

    # ------------------------------------------------------------------
    # Marketplace Detection
    # ------------------------------------------------------------------
    if "content_id" in payload or "transaction_type" in payload:
        return build_marketplace_event(**payload)

    # ------------------------------------------------------------------
    # Safety Detection
    # ------------------------------------------------------------------
    if "risk_score" in payload or "signal" in payload:
        return build_safety_event(**payload)

    # ------------------------------------------------------------------
    # No Match
    # ------------------------------------------------------------------
    raise ValueError("Unable to infer event type from payload")


# ---------------------------------------------------------------------
# ✅ Export Contract
# ---------------------------------------------------------------------

__all__ = [
    "route_event",
    "infer_and_route_event",
]