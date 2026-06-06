"""
Phase 5 — Observability & Experimentation

This package defines telemetry and experiment support for Phase 5.

## Primary Contracts

- telemetry_events.schema.json
- experiment_design.md
- metrics_catalog.md

## Role

- Record non-semantic telemetry
- Support experiment exposure / outcome tracking
- Feed offline evaluation and retraining analysis
- Provide measurement signals for learning pipelines

## Primary API

- build_telemetry_event() → construct telemetry events

## What This Layer Does

- Collect structured telemetry events
- Compute canonical metrics
- Record experiment exposure and outcomes
- Support evaluation and model validation
- Track system performance signals

## What This Layer Does NOT Do

- ❌ Does NOT change runtime behavior
- ❌ Does NOT modify semantic outputs
- ❌ Does NOT replace curator judgment
- ❌ Does NOT trigger model updates

## Downstream Consumers

- evaluation_layer → metrics consumption
- dataset_builder → feature signals
- model_validation → quality assessment
"""

from .telemetry_event_builder import (
    build_telemetry_event,
)

__all__ = [
    "build_telemetry_event",
]
