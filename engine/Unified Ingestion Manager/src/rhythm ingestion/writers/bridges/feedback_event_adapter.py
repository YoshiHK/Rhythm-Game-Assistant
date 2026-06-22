from __future__ import annotations

from typing import Any, Dict, List, Optional


def _norm_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _norm_optional_str(x: Any) -> Optional[str]:
    s = _norm_str(x)
    return s if s else None


def _norm_int(x: Any) -> Optional[int]:
    try:
        return int(x) if x not in (None, "") else None
    except Exception:
        return None


def _map_action(payload: Dict[str, Any]) -> str:
    """
    Map interpreted payload -> aggregation action vocabulary.

    Target vocabulary:
    - ignore
    - accept
    - played
    - completed
    """
    action = _norm_str(payload.get("action")).lower()
    completion_status = _norm_str(payload.get("completion_status")).lower()
    reaction_type = _norm_str(payload.get("reaction_type")).lower()

    if completion_status == "completed":
        return "completed"

    if action in {"play", "played", "start_play"}:
        return "played"

    if action in {"accept", "tip_view", "tip_accept", "view"}:
        return "accept"

    if reaction_type == "helpful":
        return "accept"

    if action == "ignore":
        return "ignore"

    return "ignore"


def adapt_interpreted_feedback_events(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert interpreted_feedback_events.json -> aggregation-compatible events.

    Concise version:
    - emits only the top-level fields most likely to satisfy the strict aggregation contract
    - intentionally avoids extra provenance / nested payload / debug fields
    """

    adapted: List[Dict[str, Any]] = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        ev = item.get("event")
        if not isinstance(ev, dict):
            continue

        ctx = ev.get("context") if isinstance(ev.get("context"), dict) else {}
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}

        row: Dict[str, Any] = {
            "event_type": "phase6.song_feedback",
            "player_id": _norm_optional_str(ctx.get("player_id") or ev.get("player_id")),
            "game_id": _norm_optional_str(ctx.get("game_id") or ev.get("game_id")),
            "recommendation_set_id": _norm_optional_str(
                ctx.get("recommendation_set_id") or ev.get("recommendation_set_id")
            ),
            "song_id": _norm_optional_str(ctx.get("song_id") or ev.get("song_id")),
            "difficulty": _norm_optional_str(ctx.get("difficulty") or ev.get("difficulty")),
            "rank": _norm_int(ctx.get("rank") if "rank" in ctx else ev.get("rank")),
            "action": _map_action(payload),
            "timestamp_utc": _norm_optional_str(ev.get("timestamp") or ev.get("timestamp_utc")),
        }

        adapted.append(row)

    return adapted


__all__ = [
    "adapt_interpreted_feedback_events",
]