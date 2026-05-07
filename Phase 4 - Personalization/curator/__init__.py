"""
Phase 4 — Curator Layer (offline, human-in-the-loop).

This package contains curator-only workflows:
- triage and review queueing
- curator label ingestion
- offline model retraining
- manual model promotion

Hard rules:
- MUST NOT be imported by runtime code paths
- MUST NOT affect live personalization behavior
- Offline and human-triggered only
"""

from .triage_queue import enqueue_for_triage
from .label_ingest import ingest_curator_labels
from .offline_retrain import retrain_offline
from .model_promotion import promote_model

__all__ = [
    "enqueue_for_triage",
    "ingest_curator_labels",
    "retrain_offline",
    "promote_model",
]