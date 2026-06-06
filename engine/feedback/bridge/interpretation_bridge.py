"""
interpretation_bridge.py

Bridge layer between:
- Phase 6 runtime feedback events (raw)
- feedback_interpreter (derived reasoning)
- Phase 5 aggregation

CRITICAL RULE:
- NEVER mutate raw feedback events
- ALWAYS attach derived reasoning separately
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from feedback.interpreter.feedback_interpreter import interpret_feedback


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def enrich_feedback_event(
    *,
    event: Dict[str, Any],
    trigger: Optional[Dict[str, Any]] = None,
    request: Optional[Dict[str, Any]] = None,
    run_result: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[Dict[str, Any]] = None,
    tips_payload: Optional[Dict[str, Any]] = None,
    personalization_context: Optional[Dict[str, Any]] = None,
    localization_context: Optional[Dict[str, Any]] = None,
    rationale: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enrich a raw feedback event with interpreter output.

    IMPORTANT:
    - Returns a NEW object
    - Does NOT mutate original event
    - Keeps raw event under `event`
    - Stores interpreter output under `derived.reason`
    """
    if not isinstance(event, dict):
        return {
            "event": event,
            "derived": {},
        }

    provenance_id = event.get("provenance_id")

    reason = interpret_feedback(
        trigger=trigger or {},
        request=request or {},
        run_result=run_result,
        diagnostics=diagnostics,
        tips_payload=tips_payload,
        personalization_context=personalization_context,
        localization_context=localization_context,
        provenance_id=provenance_id,
        rationale=rationale,
    )

    return {
        "event": dict(event),  # shallow copy, preserves raw event unchanged
        "derived": {
            "reason": reason,
        },
    }


# -----------------------------------------------------------------------------
# Optional helper for aggregation layer
# -----------------------------------------------------------------------------

def flatten_enriched_event(enriched: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten enriched structure for aggregation pipeline.

    Output shape:
    {
        ...raw event fields,
        "derived_reason": {...}
    }

    This helper is intended for downstream aggregation only.
    The original raw event should still be preserved separately.
    """
    if not isinstance(enriched, dict):
        return {}

    event = enriched.get("event") or {}
    derived = enriched.get("derived") or {}

    if not isinstance(event, dict):
        return {}

    flattened = dict(event)

    if isinstance(derived, dict) and isinstance(derived.get("reason"), dict):
        flattened["derived_reason"] = derived["reason"]

    return flattened


# -----------------------------------------------------------------------------
# Convenience wrapper for recommend.py usage (optional)
# -----------------------------------------------------------------------------

def attach_reason_to_payload(
    payload: Dict[str, Any],
    reason: Dict[str, Any],
    key: str = "feedback_reason",
) -> Dict[str, Any]:
    """
    Safe helper for UI / response usage.

    NOTE:
    - This is safe for API response / payload annotation.
    - This is NOT a replacement for raw feedback storage.
    """
    if isinstance(payload, dict):
        payload[key] = reason
    return payload


__all__ = [
    "enrich_feedback_event",
    "flatten_enriched_event",
    "attach_reason_to_payload",
]
