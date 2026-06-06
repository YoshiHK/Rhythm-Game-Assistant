"""
Phase 5 — Curator Gold & Labeling

This package defines the human-authoritative labeling layer for Phase 5.

Primary contract:
- curator_label.schema.json

Role:
- Receives curator-reviewable items from feedback aggregation
- Produces curator labels as human ground truth
- Preserves model_reason vs curator_reason distinction
- Feeds dataset construction and offline retraining

Boundary:
- Does NOT perform runtime inference
- Does NOT alter runtime behavior
- Does NOT replace human judgment
"""

from .curator_label_builder import (
    build_curator_label,
)

__all__ = [
    "build_curator_label",
]