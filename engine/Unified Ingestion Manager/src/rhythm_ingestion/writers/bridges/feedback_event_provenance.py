from __future__ import annotations

from typing import Any, Dict, List, Optional


def _norm_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _norm_optional_str(x: Any) -> Optional[str]:
    s = _norm_str(x)
    return s if s else None


def build_feedback_event_provenance(
    raw: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build provenance records from interpreted_feedback_events.json.

    PURPOSE:
    - Preserve full semantic richness from interpreted output
    - Enable debugging, auditing, explainability
    - Keep aggregation contract STRICT and separate

    This is a PURE sidecar:
    - no transformation for aggregation
    - no filtering (except malformed entries)
    - no business logic

    Output fields:
    - identity fields (for joining with aggregation rows)
    - full interpreted structures
    - metadata for traceability
    """

    provenance: List[Dict[str, Any]] = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        ev = item.get("event")
        if not isinstance(ev, dict):
            continue

        ctx = ev.get("context") if isinstance(ev.get("context"), dict) else {}
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        derived = item.get("derived")

        record: Dict[str, Any] = {
            # --------------------------------------------------
            # Identity (for joins / indexing)
            # --------------------------------------------------
            "event_type": _norm_optional_str(ev.get("event_type")),
            "event_id": _norm_optional_str(ev.get("event_id")),
            "provenance_id": _norm_optional_str(ev.get("provenance_id")),

            "player_id": _norm_optional_str(ctx.get("player_id")),
            "game_id": _norm_optional_str(ctx.get("game_id")),
            "recommendation_set_id": _norm_optional_str(ctx.get("recommendation_set_id")),
            "song_id": _norm_optional_str(ctx.get("song_id")),
            "difficulty": _norm_optional_str(ctx.get("difficulty")),
            "rank": ctx.get("rank"),

            "timestamp": _norm_optional_str(ev.get("timestamp")),

            # --------------------------------------------------
            # Raw interpreted structures (FULL fidelity)
            # --------------------------------------------------
            "context": ctx,
            "payload": payload,
            "derived": derived,

            # --------------------------------------------------
            # System metadata (trace/debug)
            # --------------------------------------------------
            "experiment": ev.get("experiment"),
            "system_context": ev.get("system_context"),
            "ingestion_metadata": ev.get("ingestion_metadata"),

            # --------------------------------------------------
            # Convenience projections (optional)
            # --------------------------------------------------
            "action_raw": payload.get("action"),
            "completion_status": payload.get("completion_status"),
            "reaction_type": payload.get("reaction_type"),
        }

        provenance.append(record)

    return provenance


__all__ = [
    "build_feedback_event_provenance",
]