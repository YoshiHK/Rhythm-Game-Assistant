"""
Phase 5 — Feedback Aggregation

This package defines raw feedback ingestion and preparation for curator review.

## Primary Contract

- feedback_events.schema.json

## Role

- Accept raw runtime feedback events
- Preserve provenance and execution context
- Maintain append-only, auditable records
- Prepare reversible inputs for curator workflows

## Primary API

- build_feedback_event() → construct feedback events

## What This Layer Does

- Receives raw feedback from event layer
- Aggregates signals by provenance_id
- Preserves original payload without modification
- Structures data for curator review
- Maintains append-only transaction log

## What This Layer Does NOT Do

- ❌ Does NOT assign reason codes
- ❌ Does NOT score quality
- ❌ Does NOT modify runtime behavior
- ❌ Does NOT produce training labels
- ❌ Does NOT perform semantic interpretation

## Downstream Consumers

- curator_queue → human review
- curator_gold → ground truth labels
- dataset_builder → training data construction
"""

from .feedback_event_builder import (
    build_feedback_event,
)

__all__ = [
    "build_feedback_event",
]
