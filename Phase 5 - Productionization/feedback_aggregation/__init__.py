"""
Phase 5 — Feedback Aggregation

This package defines raw feedback ingestion and preparation for curator review.

Primary contract:
- feedback_events.schema.json

Role:
- Accept raw runtime feedback events
- Preserve provenance and execution context
- Maintain append-only, auditable records
- Prepare reversible inputs for curator workflows

Boundary:
- Does NOT assign reason codes
- Does NOT score quality
- Does NOT modify runtime behavior
- Does NOT produce training labels
"""

from .feedback_event_builder import (
    build_feedback_event,
)

__all__ = [
    "build_feedback_event",
]