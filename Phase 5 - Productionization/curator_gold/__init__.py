"""
Phase 5 — Curator Gold & Labeling

This package defines the human-authoritative labeling layer for Phase 5.

## Primary Contract

- curator_label.schema.json

## Role

- Receives curator-reviewable items from feedback aggregation
- Produces curator labels as human ground truth
- Preserves model_reason vs curator_reason distinction
- Feeds dataset construction and offline retraining

## Primary API

- build_curator_label() → construct curator labels

## What This Layer Does

- Accept aggregated feedback units
- Apply human judgment and expertise
- Assign taxonomy-aligned reason codes
- Compare model predictions with human labels
- Produce deterministic, auditable curation records

## What This Layer Does NOT Do

- ❌ Does NOT auto-label feedback
- ❌ Does NOT modify runtime behavior
- ❌ Does NOT filter or delete data
- ❌ Does NOT perform semantic reasoning beyond taxonomy

## Downstream Consumers

- dataset_builder → feature + label construction
- offline_retrain → model training signal
- evaluation → quality measurement
"""

from .curator_label_builder import (
    build_curator_label,
)

__all__ = [
    "build_curator_label",
]
