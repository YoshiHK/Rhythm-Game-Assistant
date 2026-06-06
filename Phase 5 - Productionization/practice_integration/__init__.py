"""
Phase 5 — Practice Integration & In-Session Experience

This package defines practice-facing telemetry generation and integration helpers.

Primary contract:
- practice_telemetry.schema.json

Role:
- Record practice-session events
- Capture hint interactions and replay / retry behavior
- Preserve provenance linkage into feedback, telemetry, and learning systems

Boundary:
- Does NOT change recommendation semantics
- Does NOT generate training labels
- Does NOT alter runtime model logic
"""

from .practice_telemetry_event_builder import (
    build_practice_telemetry_event,
)

__all__ = [
    "build_practice_telemetry_event",
]