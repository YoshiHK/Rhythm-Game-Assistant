from __future__ import annotations

"""
triage_queue.py

Phase 4 — Curator Triage Queue.

Purpose:
- Prepare Phase 4 artifacts for human review
- Does NOT perform labeling or training
- Does NOT affect runtime behavior

Typical triggers:
- safety flags
- low confidence decisions
- experimental variants
"""

from typing import Any, Dict
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def enqueue_for_triage(
    *,
    request_id: str,
    payload_hash: str,
    provenance: Dict[str, Any],
    reason: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Build a triage queue entry (append-only record).

    Output is intended for storage in a curator-facing system.
    """

    entry: Dict[str, Any] = {
        "triage_id": f"triage::{request_id}",
        "timestamp": _utc_now_iso(),
        "target": {
            "request_id": request_id,
            "payload_hash": payload_hash,
        },
        "reason": str(reason),
        "provenance_ref": provenance,
    }

    if metadata:
        entry["metadata"] = dict(metadata)

    return entry


__all__ = ["enqueue_for_triage"]