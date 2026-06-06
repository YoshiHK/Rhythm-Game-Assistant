"""
engine.feedback.bridge

Bridge layer between runtime feedback and Phase 5 aggregation.

Purpose:
- Safely enrich raw feedback events with derived reasoning
- Maintain strict separation between:
  - raw feedback (immutable)
  - derived interpretation

Key API:
- enrich_feedback_event

Rules:
- NEVER mutate input event
- ALWAYS attach derived reasoning separately
- Must NOT introduce semantic leakage into raw layer
"""

from .interpretation_bridge import (
    enrich_feedback_event,
    flatten_enriched_event,
    attach_reason_to_payload,
)

__all__ = [
    "enrich_feedback_event",
    "flatten_enriched_event",
    "attach_reason_to_payload",
]