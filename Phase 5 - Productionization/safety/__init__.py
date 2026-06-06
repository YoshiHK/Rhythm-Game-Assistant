"""
Phase 5 — Safety, Legal, and Anti-Cheat

This package defines structured safety-event generation for Phase 5.

Primary contracts:
- safety_events.schema.json
- anti_cheat_signals.md
- legal_compliance.md
- escalation_policy.md

Role:
- Record safety-relevant events
- Structure anti-cheat / abuse / compliance signals
- Support escalation to Phase 6 enforcement systems

Boundary:
- Does NOT block runtime execution
- Does NOT penalize users directly
- Does NOT replace Phase 6 enforcement authority
"""

from .safety_event_builder import (
    build_safety_event,
)

__all__ = [
    "build_safety_event",
]