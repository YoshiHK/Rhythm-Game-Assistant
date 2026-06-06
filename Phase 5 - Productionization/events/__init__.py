"""
Phase 5 — Events Layer (ENTRY GATEWAY)

This package defines the ONLY valid entry point into Phase 5.

Core Concept:
---------------
All raw signals MUST be converted into structured events
before entering any Phase 5 pipeline.

This layer enforces:

    signal → event_router → builder → schema → pipeline

Primary Responsibilities:
---------------
- Route raw input payloads into the correct event builder
- Enforce event construction discipline
- Ensure all events conform to Phase 5 data contracts

Supported Event Types:
---------------
- feedback_event
- telemetry_event
- marketplace_event
- safety_event

Primary API:
---------------
- route_event() → strict routing
- infer_and_route_event() → optional fallback

Non-Responsibilities:
---------------
- No business logic
- No interpretation
- No learning or evaluation
- No schema definition (delegated to each layer)
- No direct builder exposure

Contract (CRITICAL):
---------------
- ALL Phase 5 ingestion MUST go through event_router
- Direct usage of builders is NOT allowed outside this layer
- Only structured events may enter Phase 5 pipelines

Design Guarantee:
---------------
This layer enforces the Phase 5 ENTRY CONTRACT.

If bypassed:
    → Phase 5 contract is broken
"""

from .event_router import (
    route_event,
    infer_and_route_event,
)

__all__ = [
    "route_event",
    "infer_and_route_event",
]