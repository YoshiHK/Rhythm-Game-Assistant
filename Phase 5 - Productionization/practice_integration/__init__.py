"""
Phase 5 — Practice Integration & In-Session Experience

This package defines practice-facing telemetry generation and integration helpers.

## Primary Contract

- practice_telemetry.schema.json

## Role

- Record practice-session events
- Capture hint interactions and replay / retry behavior
- Preserve provenance linkage into feedback, telemetry, and learning systems
- Support in-session experience and guidance delivery

## Primary API

- build_practice_telemetry_event() → construct practice events

## What This Layer Does

- Render recommendations and hints
- Map system outputs into gameplay context
- Capture user interaction signals
- Record telemetry for downstream analysis
- Support practice mode integration

## What This Layer Does NOT Do

- ❌ Does NOT change recommendation semantics
- ❌ Does NOT generate training labels
- ❌ Does NOT alter runtime model logic
- ❌ Does NOT bypass Phase 6 control

## Upstream Source

- recommendation → structured output
- Phase 6 runtime → in-session execution

## Downstream Consumers

- telemetry → signal collection
- feedback_aggregation → user reactions
- evaluation → engagement metrics
"""

from .practice_telemetry_event_builder import (
    build_practice_telemetry_event,
)

__all__ = [
    "build_practice_telemetry_event",
]
