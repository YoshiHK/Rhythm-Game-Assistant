"""
Phase 5 — Safety, Legal, and Anti-Cheat

This package defines structured safety-event generation for Phase 5.

## Primary Contracts

- safety_events.schema.json
- anti_cheat_signals.md
- legal_compliance.md
- escalation_policy.md

## Role

- Record safety-relevant events
- Structure anti-cheat / abuse / compliance signals
- Support escalation to Phase 6 enforcement systems
- Enable evidence-based enforcement decisions

## Primary API

- build_safety_event() → construct safety events

## What This Layer Does

- Detect risk signals (anti-cheat / misuse)
- Structure signals into safety_events
- Classify severity
- Record decisions (non-enforcing)
- Escalate to Phase 6

## What This Layer Does NOT Do

- ❌ Does NOT block runtime execution
- ❌ Does NOT apply penalties
- ❌ Does NOT modify recommendations
- ❌ Does NOT define legal outcomes

## Core Model

    signal → classification → decision → safety_event → escalation

## Upstream Sources

- telemetry → system behavior
- feedback → user reaction
- marketplace → economic signals

## Downstream Consumers

- escalation_queue → Phase 6 enforcement
- safety_review → manual adjudication
- audit_log → compliance tracking
"""

from .safety_event_builder import (
    build_safety_event,
)

__all__ = [
    "build_safety_event",
]
