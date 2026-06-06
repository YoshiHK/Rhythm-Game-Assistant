from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime

from feedback.bridge.interpretation_bridge import enrich_feedback_event


# ---------------------------------------------------------------------
# Configuration / summary
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class AggregationConfig:
    """
    Aggregation configuration.

    Notes:
    - event_type is optional. If provided, only events with matching event_type
      are considered valid.
    - action_priority determines which action wins when multiple feedback events
      refer to the same recommended item.
    - attach_derived_reason controls whether interpreter output is copied into
      aggregated rows.
    """
    event_type: Optional[str] = None
    action_priority: Tuple[str, ...] = (
        "accepted",
        "completed",
        "clicked",
        "used",
        "dismissed",
        "skipped",
        "shown",
    )
    attach_derived_reason: bool = True


@dataclass(frozen=True)
class AggregationSummary:
    total_events_in: int
    total_events_used: int
    total_events_dropped: int
    unique_items: int
    outcome_counts: Dict[str, int]


# ---------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------

def _parse_iso8601(s: Any) -> Optional[datetime]:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _norm_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _norm_optional_str(x: Any) -> Optional[str]:
    s = _norm_str(x)
    return s if s else None


def _norm_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _priority_index(action: str, priority: Tuple[str, ...]) -> int:
    try:
        return priority.index(action)
    except ValueError:
        return -1


def _extract_action(evt: Dict[str, Any]) -> str:
    """
    Best-effort action extraction.

    Prefers:
    1) top-level action
    2) payload.action
    3) event_type (fallback)
    """
    action = _norm_str(evt.get("action"))
    if action:
        return action

    payload = evt.get("payload")
    if isinstance(payload, dict):
        action = _norm_str(payload.get("action"))
        if action:
            return action

    return _norm_str(evt.get("event_type"))


def _payload_overlay(evt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a non-mutating merged view of the event:
    - top-level fields win
    - payload fields backfill missing top-level ones

    This keeps raw events unchanged while allowing aggregation helpers
    to work with either top-level or payload-scoped fields.
    """
    if not isinstance(evt, dict):
        return {}

    out = dict(evt)
    payload = evt.get("payload")
    if isinstance(payload, dict):
        for k, v in payload.items():
            out.setdefault(k, v)
    return out


def _item_key(evt: Dict[str, Any]) -> Tuple[str, str, str, str, Optional[str], Optional[int]]:
    """
    Key for a single recommended item exposure.
    """
    return (
        _norm_str(evt.get("player_id")),
        _norm_str(evt.get("game_id")),
        _norm_str(evt.get("recommendation_set_id")),
        _norm_str(evt.get("song_id")),
        _norm_optional_str(evt.get("difficulty")),
        _norm_int(evt.get("rank")),
    )


def _has_minimum_identity(evt: Dict[str, Any]) -> bool:
    """
    Require enough identity to aggregate to selection/item level.
    """
    return bool(
        _norm_str(evt.get("player_id"))
        and _norm_str(evt.get("game_id"))
        and _norm_str(evt.get("recommendation_set_id"))
        and _norm_str(evt.get("song_id"))
    )


def _is_valid_event(evt: Dict[str, Any], cfg: AggregationConfig) -> bool:
    if not isinstance(evt, dict):
        return False

    if cfg.event_type is not None:
        if _norm_str(evt.get("event_type")) != _norm_str(cfg.event_type):
            return False

    if not _has_minimum_identity(evt):
        return False

    return True


def _safe_row(evt: Dict[str, Any], action: str) -> Dict[str, Any]:
    """
    Convert event -> safe, selection-level row fragment.
    This remains aggregation-safe and does not mutate raw feedback.
    """
    return {
        "player_id": _norm_str(evt.get("player_id")),
        "game_id": _norm_str(evt.get("game_id")),
        "recommendation_set_id": _norm_str(evt.get("recommendation_set_id")),
        "song_id": _norm_str(evt.get("song_id")),
        "difficulty": _norm_optional_str(evt.get("difficulty")),
        "rank": _norm_int(evt.get("rank")),
        "action": action,
        "timestamp_utc": _norm_str(evt.get("timestamp_utc") or evt.get("timestamp")),
        "tier_id": _norm_optional_str(evt.get("tier_id")),
        "target_metric": _norm_float(evt.get("target_metric")),
        "catalog_fingerprint": _norm_optional_str(evt.get("catalog_fingerprint")),
        "locale": _norm_optional_str(evt.get("locale")),
        "session_id": _norm_optional_str(evt.get("session_id")),
        "provenance_id": _norm_optional_str(evt.get("provenance_id")),
        "event_id": _norm_optional_str(evt.get("event_id")),
        "source_type": _norm_optional_str(evt.get("source_type")),
        "event_type": _norm_optional_str(evt.get("event_type")),
    }


def _is_better_candidate(
    candidate: Dict[str, Any],
    incumbent: Dict[str, Any],
    *,
    priority: Tuple[str, ...],
) -> bool:
    """
    Decide whether candidate should replace incumbent for same item key.

    Rules:
    1) Higher action priority wins
    2) If same priority, later timestamp wins
    """
    cand_action = _norm_str(candidate.get("action"))
    inc_action = _norm_str(incumbent.get("action"))

    cand_pri = _priority_index(cand_action, priority)
    inc_pri = _priority_index(inc_action, priority)

    if cand_pri != inc_pri:
        return cand_pri > inc_pri

    cand_ts = _parse_iso8601(candidate.get("timestamp_utc"))
    inc_ts = _parse_iso8601(incumbent.get("timestamp_utc"))

    if cand_ts and inc_ts:
        return cand_ts > inc_ts

    if cand_ts and not inc_ts:
        return True

    return False


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def aggregate_song_feedback_events(
    events: Iterable[Dict[str, Any]],
    *,
    config: AggregationConfig = AggregationConfig(),
) -> Dict[str, Any]:
    """
    Aggregate forward-only Song Recommendation feedback events (Phase 6 -> Phase 5).

    Output:
    {
        "rows": [...],
        "summary": {...}
    }

    Notes:
    - Raw feedback events are never mutated.
    - Interpreter output is attached only to aggregated rows (derived_* fields).
    """
    total_in = 0
    total_dropped = 0
    outcome_counts: Dict[str, int] = {}

    best_by_item: Dict[
        Tuple[str, str, str, str, Optional[str], Optional[int]],
        Dict[str, Any]
    ] = {}

    for raw_evt in events:
        total_in += 1

        # Create a merged read-only view for aggregation convenience
        evt = _payload_overlay(raw_evt)

        if not _is_valid_event(evt, config):
            total_dropped += 1
            continue

        action = _extract_action(evt)
        row = _safe_row(evt, action)

        # ---------------------------------------------------------
        # Bridge: raw event -> derived interpreter output
        # ---------------------------------------------------------
        enriched = enrich_feedback_event(
            event=raw_evt,  # keep RAW event source unchanged
            trigger=evt.get("trigger") if isinstance(evt.get("trigger"), dict) else None,
            request=evt.get("request") if isinstance(evt.get("request"), dict) else None,
            run_result=evt.get("run_result") if isinstance(evt.get("run_result"), dict) else None,
            diagnostics=evt.get("diagnostics") if isinstance(evt.get("diagnostics"), dict) else None,
            tips_payload=evt.get("tips_payload") if isinstance(evt.get("tips_payload"), dict) else None,
            personalization_context=evt.get("personalization_context") if isinstance(evt.get("personalization_context"), dict) else None,
            localization_context=evt.get("localization_context") if isinstance(evt.get("localization_context"), dict) else None,
            rationale=evt.get("rationale") if isinstance(evt.get("rationale"), dict) else None,
        )

        derived = enriched.get("derived") if isinstance(enriched, dict) else {}
        reason = derived.get("reason") if isinstance(derived, dict) else {}

        if config.attach_derived_reason and isinstance(reason, dict):
            row["derived_reason_codes"] = list(reason.get("reason_codes") or [])
            row["derived_primary_reason"] = _norm_optional_str(reason.get("primary_reason"))
            row["derived_reason_confidence"] = _norm_float(reason.get("confidence"))

        k = _item_key(evt)
        incumbent = best_by_item.get(k)

        if incumbent is None or _is_better_candidate(row, incumbent, priority=config.action_priority):
            best_by_item[k] = row

    rows = list(best_by_item.values())

    for row in rows:
        action = _norm_str(row.get("action"))
        if action:
            outcome_counts[action] = outcome_counts.get(action, 0) + 1

    summary = AggregationSummary(
        total_events_in=total_in,
        total_events_used=len(rows),
        total_events_dropped=total_dropped,
        unique_items=len(rows),
        outcome_counts=outcome_counts,
    )

    return {
        "rows": rows,
        "summary": asdict(summary),
    }


__all__ = [
    "AggregationConfig",
    "AggregationSummary",
    "aggregate_song_feedback_events",
]