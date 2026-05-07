from __future__ import annotations

"""
event_logger.py

Phase 4 — Events Layer: Event Logger (observational, append-only)

Builds dictionaries that conform to:
- PHASE_4_EVENT_LOG.schema.json

Hard constraints:
- No persistence
- No PII (player_id must be hashed upstream)
- No raw canonical payload stored (only request_id + payload_hash)
- Downstream-only: must not influence Phase 1–3 semantics
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


PHASE4_EVENT_TYPES = {
    "phase4.request",
    "phase4.decision",
    "phase4.render",
    "phase4.ui_interaction",
    "phase4.feedback",
    "phase4.error",
}


def build_phase4_event_log_entry(
    *,
    event_id: str,
    event_type: str,
    request_id: str,
    payload_hash: str,
    game_id: str,
    event_timestamp: Optional[str] = None,
    # request optional
    session_id: Optional[str] = None,
    player_id_hash: Optional[str] = None,
    engine_mode: Optional[str] = None,  # deterministic|personalized|debug
    locale: Optional[str] = None,
    # context optional
    song_id: Optional[Any] = None,
    difficulty_label: Optional[str] = None,
    app_version: Optional[str] = None,
    model_bundle_version: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
    # optional blocks
    decision: Optional[Dict[str, Any]] = None,
    ui: Optional[Dict[str, Any]] = None,
    feedback: Optional[Dict[str, Any]] = None,
    outcome: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build an event log record conforming to PHASE_4_EVENT_LOG.schema.json.

    Notes:
    - This function only constructs a dict; it does not persist.
    - No raw canonical payload stored; only request_id + payload_hash.
    """

    if event_type not in PHASE4_EVENT_TYPES:
        raise ValueError(f"Invalid Phase 4 event_type: {event_type}")

    evt: Dict[str, Any] = {
        "event_id": str(event_id),
        "event_type": str(event_type),
        "event_timestamp": str(event_timestamp or _utc_now_iso()),
        "request": {
            "request_id": str(request_id),
            "payload_hash": str(payload_hash),
        },
        "context": {
            "game_id": str(game_id),
        },
    }

    # request optional fields
    if session_id:
        evt["request"]["session_id"] = str(session_id)
    if player_id_hash:
        evt["request"]["player_id_hash"] = str(player_id_hash)
    if engine_mode:
        evt["request"]["engine_mode"] = str(engine_mode)
    if locale:
        evt["request"]["locale"] = str(locale)

    # context optional fields
    if song_id is not None:
        evt["context"]["song_id"] = song_id
    if difficulty_label:
        evt["context"]["difficulty_label"] = str(difficulty_label)
    if app_version:
        evt["context"]["app_version"] = str(app_version)
    if model_bundle_version:
        evt["context"]["model_bundle_version"] = str(model_bundle_version)
    if feature_flags is not None:
        evt["context"]["feature_flags"] = dict(feature_flags)

    # optional blocks (must remain schema-shaped; caller responsibility)
    if decision is not None:
        evt["decision"] = dict(decision)
    if ui is not None:
        evt["ui"] = dict(ui)
    if feedback is not None:
        evt["feedback"] = dict(feedback)
    if outcome is not None:
        evt["outcome"] = dict(outcome)

    return evt


def build_phase4_feedback_event(
    *,
    event_id: str,
    feedback_record: Dict[str, Any],
    game_id: str,
    request_id: str,
    payload_hash: str,
    event_timestamp: Optional[str] = None,
    session_id: Optional[str] = None,
    player_id_hash: Optional[str] = None,
    engine_mode: Optional[str] = None,
    locale: Optional[str] = None,
    song_id: Optional[Any] = None,
    difficulty_label: Optional[str] = None,
    app_version: Optional[str] = None,
    model_bundle_version: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convenience builder:
    Convert a feedback capture record into a phase4.feedback event entry.

    This follows the PHASE_4_EVENT_LOG.schema.json "feedback" block.
    """

    signal = feedback_record.get("signal") if isinstance(feedback_record, dict) else None
    reason = feedback_record.get("reason") if isinstance(feedback_record, dict) else None

    fb: Dict[str, Any] = {}
    if isinstance(signal, dict):
        if "helpful" in signal:
            fb["helpful"] = bool(signal.get("helpful"))
        if "flagged" in signal:
            fb["flagged"] = bool(signal.get("flagged"))

    if isinstance(reason, dict):
        if reason.get("reason_code") is not None:
            fb["reason_code"] = str(reason.get("reason_code"))
        if reason.get("comment"):
            fb["comment"] = str(reason.get("comment"))

    return build_phase4_event_log_entry(
        event_id=event_id,
        event_type="phase4.feedback",
        event_timestamp=event_timestamp,
        request_id=request_id,
        payload_hash=payload_hash,
        game_id=game_id,
        session_id=session_id,
        player_id_hash=player_id_hash,
        engine_mode=engine_mode,
        locale=locale,
        song_id=song_id,
        difficulty_label=difficulty_label,
        app_version=app_version,
        model_bundle_version=model_bundle_version,
        feature_flags=feature_flags,
        feedback=fb,
    )


__all__ = [
    "PHASE4_EVENT_TYPES",
    "build_phase4_event_log_entry",
    "build_phase4_feedback_event",
]