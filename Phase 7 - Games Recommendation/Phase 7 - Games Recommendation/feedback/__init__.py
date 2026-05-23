"""
Phase 7 — Feedback Layer

This package defines canonical feedback capture and forwarding
for Game Recommendations.

Contract (Non-Negotiable):
- Feedback is forward-only and observational.
- Runtime recommendation logic MUST NOT depend on feedback outcomes.
- Feedback MUST NOT trigger ranking adaptation at runtime.

Learning Loop Policy:
- Phase 7 MAY emit structured feedback events.
- Phase 5 is the ONLY phase allowed to aggregate, learn from,
  or retrain based on these events.
- Any learning outcome MUST be introduced via
  validated deployment (never inline adaptation).

This guarantees that Phase 7 remains:
- deterministic
- explainable
- auditable
- reversible
"""

from feedback.feedback_forwarder import (
    Phase7FeedbackEvent,
    FeedbackAction,
    emit_feedback_event,
)

__all__ = [
    "Phase7FeedbackEvent",
    "FeedbackAction",
    "emit_feedback_event",
]