"""
trace_utils.py

engine/feedback/diagnostics/

Purpose:
- Provide lightweight tracing helpers for feedback interpretation flow
- Build non-mutating debug traces across runtime -> bridge -> aggregation -> curator
- Keep traces deterministic and side-effect free

Non-goals:
- No file writes
- No logging side effects
- No schema enforcement
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def build_feedback_trace(
    *,
    event: Optional[Dict[str, Any]] = None,
    enriched: Optional[Dict[str, Any]] = None,
    aggregated_row: Optional[Dict[str, Any]] = None,
    curator_item: Optional[Dict[str, Any]] = None,
    training_sample: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a compact lineage trace across the feedback pipeline.
    """
    evt = event if isinstance(event, dict) else {}
    enr = enriched if isinstance(enriched, dict) else {}
    row = aggregated_row if isinstance(aggregated_row, dict) else {}
    cur = curator_item if isinstance(curator_item, dict) else {}
    samp = training_sample if isinstance(training_sample, dict) else {}

    derived = enr.get("derived") if isinstance(enr.get("derived"), dict) else {}
    reason = derived.get("reason") if isinstance(derived.get("reason"), dict) else {}

    return {
        "identity": {
            "event_id": _first_nonempty(evt.get("event_id"), row.get("event_id"), cur.get("event_id")),
            "provenance_id": _first_nonempty(evt.get("provenance_id"), row.get("provenance_id"), cur.get("provenance_id"), samp.get("provenance_id")),
            "curation_id": _first_nonempty(cur.get("curation_id"), samp.get("curation_id")),
        },
        "runtime": {
            "event_type": _as_str(evt.get("event_type")),
            "source_type": _as_str(evt.get("source_type")),
            "timestamp": _as_str(evt.get("timestamp")),
        },
        "interpretation": {
            "primary_reason": _as_str(reason.get("primary_reason")),
            "reason_codes": reason.get("reason_codes") if isinstance(reason.get("reason_codes"), list) else [],
            "confidence": reason.get("confidence"),
        },
        "aggregation": {
            "game_id": _as_str(row.get("game_id")),
            "song_id": _as_str(row.get("song_id")),
            "rank": row.get("rank"),
            "action": _as_str(row.get("action")),
            "derived_primary_reason": _as_str(row.get("derived_primary_reason")),
        },
        "curation": {
            "curator_primary_reason": _read_nested(cur, "curator_reason", "primary_reason"),
            "agreement_type": _read_nested(cur, "judgement", "agreement_type"),
        },
        "training": {
            "label": _as_str(samp.get("label")),
            "gold_labels_count": len(samp.get("gold_labels") or []) if isinstance(samp.get("gold_labels"), list) else 0,
        },
    }


def trace_reason_path(
    *,
    event: Optional[Dict[str, Any]] = None,
    enriched: Optional[Dict[str, Any]] = None,
    curator_item: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Focused trace for reason evolution:
    raw event -> machine reason -> curator reason.
    """
    evt = event if isinstance(event, dict) else {}
    enr = enriched if isinstance(enriched, dict) else {}
    cur = curator_item if isinstance(curator_item, dict) else {}

    derived = enr.get("derived") if isinstance(enr.get("derived"), dict) else {}
    model_reason = derived.get("reason") if isinstance(derived.get("reason"), dict) else {}
    curator_reason = cur.get("curator_reason") if isinstance(cur.get("curator_reason"), dict) else {}

    return {
        "event_id": _as_str(evt.get("event_id") or cur.get("event_id")),
        "provenance_id": _as_str(evt.get("provenance_id") or cur.get("provenance_id")),
        "model_reason": {
            "primary_reason": _as_str(model_reason.get("primary_reason")),
            "reason_codes": model_reason.get("reason_codes") if isinstance(model_reason.get("reason_codes"), list) else [],
            "confidence": model_reason.get("confidence"),
        },
        "curator_reason": {
            "primary_reason": _as_str(curator_reason.get("primary_reason")),
            "reason_codes": curator_reason.get("reason_codes") if isinstance(curator_reason.get("reason_codes"), list) else [],
            "category": _as_str(curator_reason.get("category")),
            "layer": _as_str(curator_reason.get("layer")),
        },
        "judgement": cur.get("judgement") if isinstance(cur.get("judgement"), dict) else {},
    }


def _as_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _first_nonempty(*values: Any) -> Optional[str]:
    for v in values:
        s = _as_str(v)
        if s:
            return s
    return None


def _read_nested(obj: Dict[str, Any], *path: str) -> Optional[str]:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    s = _as_str(cur)
    return s if s else None


__all__ = [
    "build_feedback_trace",
    "trace_reason_path",
]
