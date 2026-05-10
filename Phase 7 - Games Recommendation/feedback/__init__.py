"""
Phase 7 — Feedback Layer

This package defines feedback capture and forwarding contracts.
Runtime recommendation logic MUST NOT depend on feedback outcomes.
"""

from .feedback_forwarder import (
    Phase7FeedbackEvent,
    FeedbackAction,
    emit_feedback_event,
)

__all__ = [
    "Phase7FeedbackEvent",
    "FeedbackAction",
    "emit_feedback_event",
]