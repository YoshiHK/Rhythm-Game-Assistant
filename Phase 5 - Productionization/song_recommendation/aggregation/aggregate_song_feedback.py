from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
from datetime import datetime


@dataclass(frozen=True)
class AggregationConfig:
    """
    Aggregation configuration.

    Keep this layer purely mechanical:
    - deterministic
    - schema-light
    - selection-level only
    """
    # Filter: only process events matching this event_type
    event_type: str = "phase6.song_feedback"

    # Action priority (higher wins) used to compute final_outcome per item
    # completed > played > accept > ignore
    action_priority: Tuple[str, ...] = ("ignore", "accept", "played", "completed")

    # If True, drop events with missing required fields rather than raising
    drop_invalid: bool = True

    # If True, keep only a whitelist of safe (non-semantic) columns in output rows
    strict_safe_columns: bool = True


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
        # datetime.fromisoformat supports many ISO-8601 forms; keep best-effort
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
        # Unknown actions are treated as lowest priority (ignored in outcome)
        return -1


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


def _is_valid_event(evt: Dict[str, Any], cfg: AggregationConfig) -> bool:
    if not isinstance(evt, dict):
        return False
    if _norm_str(evt.get("event_type")) != cfg.event_type:
        return False

    # Required fields for aggregation identity
    required = ["player_id", "game_id", "recommendation_set_id", "song_id", "action", "timestamp_utc"]
    for k in required:
        if not _norm_str(evt.get(k)):
            return False

    return True


def _safe_row(evt: Dict[str, Any], action: str, cfg: AggregationConfig) -> Dict[str, Any]:
    """
    Convert event -> safe, selection-level row fragment (no semantics).
    """
    row: Dict[str, Any] = {
        "player_id": _norm_str(evt.get("player_id")),
        "game_id": _norm_str(evt.get("game_id")),
        "recommendation_set_id": _norm_str(evt.get("recommendation_set_id")),
        "song_id": _norm_str(evt.get("song_id")),
        "difficulty": _norm_optional_str(evt.get("difficulty")),
        "rank": _norm_int(evt.get("rank")),
        "action": action,
        "timestamp_utc": _norm_str(evt.get("timestamp_utc")),
        "tier_id": _norm_optional_str(evt.get("tier_id")),
        "target_metric": _norm_float(evt.get("target_metric")),
        "catalog_fingerprint": _norm_optional_str(evt.get("catalog_fingerprint")),
        "locale": _norm_optional_str(evt.get("locale")),
        "session_id": _norm_optional_str(evt.get("session_id")),
    }

    if not cfg.strict_safe_columns:
        # If you ever need additional fields, add them explicitly—do not pass through blindly.
        pass

    return row


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
        "rows": [ ... ],         # aggregated per item exposure
        "summary": { ... }       # AggregationSummary as dict
      }

    Aggregation rules (deterministic):
    - Group by (player_id, game_id, recommendation_set_id, song_id, difficulty, rank)
    - Determine final_outcome by highest priority action seen
    - Record first_seen_utc / last_seen_utc
    - Count actions per item
    """
    cfg = config
    priority = cfg.action_priority

    total_in = 0
    used = 0
    dropped = 0

    # Per-item accumulator
    acc: Dict[Tuple[str, str, str, str, Optional[str], Optional[int]], Dict[str, Any]] = {}

    for evt in events:
        total_in += 1
        if not isinstance(evt, dict) or not _is_valid_event(evt, cfg):
            dropped += 1
            if cfg.drop_invalid:
                continue
            raise ValueError(f"Invalid event for aggregation: {evt}")

        action = _norm_str(evt.get("action")).lower()
        if _priority_index(action, priority) < 0:
            # Unknown action: drop (mechanical, deterministic)
            dropped += 1
            if cfg.drop_invalid:
                continue
            raise ValueError(f"Unknown action: {action}")

        used += 1
        key = _item_key(evt)
        ts = _parse_iso8601(evt.get("timestamp_utc"))

        frag = _safe_row(evt, action, cfg)

        if key not in acc:
            acc[key] = {
                "player_id": frag["player_id"],
                "game_id": frag["game_id"],
                "recommendation_set_id": frag["recommendation_set_id"],
                "song_id": frag["song_id"],
                "difficulty": frag["difficulty"],
                "rank": frag["rank"],
                "tier_id": frag["tier_id"],
                "target_metric": frag["target_metric"],
                "catalog_fingerprint": frag["catalog_fingerprint"],
                "locale": frag["locale"],
                "session_id": frag["session_id"],
                "first_seen_utc": frag["timestamp_utc"],
                "last_seen_utc": frag["timestamp_utc"],
                "action_counts": {a: 0 for a in priority},
                "final_outcome": action,
                "_final_priority": _priority_index(action, priority),
                "_first_ts": ts,
                "_last_ts": ts,
            }

        item = acc[key]

        # Update counts
        item["action_counts"][action] = int(item["action_counts"].get(action, 0)) + 1

        # Update time bounds deterministically using parsed timestamps when available
        if ts is not None:
            if item["_first_ts"] is None or ts < item["_first_ts"]:
                item["_first_ts"] = ts
                item["first_seen_utc"] = frag["timestamp_utc"]
            if item["_last_ts"] is None or ts > item["_last_ts"]:
                item["_last_ts"] = ts
                item["last_seen_utc"] = frag["timestamp_utc"]
        else:
            # If unparsable, still keep last_seen as last processed (deterministic order)
            item["last_seen_utc"] = frag["timestamp_utc"]

        # Update final outcome by priority
        p = _priority_index(action, priority)
        if p > item["_final_priority"]:
            item["_final_priority"] = p
            item["final_outcome"] = action

        # Keep catalog_fingerprint if missing previously
        if item.get("catalog_fingerprint") is None and frag.get("catalog_fingerprint") is not None:
            item["catalog_fingerprint"] = frag["catalog_fingerprint"]

        # Keep locale if missing previously
        if item.get("locale") is None and frag.get("locale") is not None:
            item["locale"] = frag["locale"]

    # Materialize output rows (stable order)
    keys_sorted = sorted(acc.keys(), key=lambda k: (k[0], k[1], k[2], k[5] if k[5] is not None else 10**9, k[3]))
    rows: List[Dict[str, Any]] = []

    outcome_counts: Dict[str, int] = {a: 0 for a in cfg.action_priority}

    for k in keys_sorted:
        item = acc[k]
        # Remove internal fields
        item.pop("_final_priority", None)
        item.pop("_first_ts", None)
        item.pop("_last_ts", None)

        out = dict(item)
        # Ensure action_counts only contains known actions (stable)
        out["action_counts"] = {a: int(out["action_counts"].get(a, 0)) for a in cfg.action_priority}

        outcome_counts[out["final_outcome"]] = int(outcome_counts.get(out["final_outcome"], 0)) + 1
        rows.append(out)

    summary = AggregationSummary(
        total_events_in=total_in,
        total_events_used=used,
        total_events_dropped=dropped,
        unique_items=len(rows),
        outcome_counts=outcome_counts,
    )

    return {
        "rows": rows,
        "summary": asdict(summary),
    }