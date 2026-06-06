"""
Phase 5 — Marketplace & Creator Flows

This package defines marketplace-facing event construction and contracts.

Intended primary contract:
- marketplace_events.schema.json

Role:
- Record content lifecycle events
- Record creator-program activity
- Record marketplace interactions and transactions
- Support traceability into telemetry, safety, and learning systems

Boundary:
- Does NOT perform recommendation logic
- Does NOT enforce penalties
- Does NOT alter runtime semantics
"""

from .marketplace_event_builder import (
    build_marketplace_event,
)

__all__ = [
    "build_marketplace_event",
]