"""
Phase 5 — Marketplace & Creator Flows

This package defines marketplace-facing event construction and contracts.

## Primary Contract

- marketplace_event.schema.json

## Role

- Record content lifecycle events
- Record creator-program activity
- Record marketplace interactions and transactions
- Support traceability into telemetry, safety, and learning systems

## Primary API

- build_marketplace_event() → construct marketplace events

## What This Layer Does

- Manage content lifecycle
- Record marketplace interactions
- Enable creator participation
- Support monetization flows
- Produce marketplace_events
- Track engagement metrics

## What This Layer Does NOT Do

- ❌ Does NOT perform recommendation logic
- ❌ Does NOT enforce penalties (delegated to safety)
- ❌ Does NOT define gameplay semantics
- ❌ Does NOT modify runtime decisions

## Downstream Consumers

- telemetry → behavior analysis
- feedback → player reaction capture
- safety → abuse detection
- learning → economic signal analysis
"""

from .marketplace_event_builder import (
    build_marketplace_event,
)

__all__ = [
    "build_marketplace_event",
]
