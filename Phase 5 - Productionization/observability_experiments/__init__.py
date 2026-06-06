"""
Phase 5 — Observability & Experimentation

This package defines telemetry and experiment support for Phase 5.

Primary contracts:
- telemetry_events.schema.json
- metrics_catalog.md
- experiment_design.md
- feature_flags.md

Role:
- Record non-semantic telemetry
- Support experiment exposure / outcome tracking
- Feed offline evaluation and retraining analysis

Boundary:
- Does NOT change runtime behavior
- Does NOT modify semantic outputs
- Does NOT replace curator judgment
"""

from .telemetry_event_builder import (
    build_telemetry_event,
)

__all__ = [
    "build_telemetry_event",
]