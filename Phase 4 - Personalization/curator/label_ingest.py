from __future__ import annotations

"""
label_ingest.py

Phase 4 — Curator Label Ingestion.

Consumes curator labels that conform to:
- curator_label.schema.json

This module:
- validates shape at a high level
- prepares labels for offline training or audit
"""

from typing import Any, Dict, List


REQUIRED_FIELDS = {
    "label_id",
    "curator_id",
    "label_timestamp",
    "target",
    "decision",
}


def ingest_curator_labels(labels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and normalize curator labels.

    Invalid labels are dropped silently.
    """

    ingested: List[Dict[str, Any]] = []

    for lbl in labels:
        if not isinstance(lbl, dict):
            continue
        if not REQUIRED_FIELDS.issubset(lbl.keys()):
            continue

        ingested.append(lbl)

    return ingested


__all__ = ["ingest_curator_labels"]