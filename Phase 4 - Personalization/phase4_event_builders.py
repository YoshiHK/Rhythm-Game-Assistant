
#!/usr/bin/env python3
"""phase4_event_builders.py

Phase 4 event builder helpers.

Provides:
- build_phase4_event_log_entry: constructs events matching PHASE_4_EVENT_LOG.schema.json
- build_phase4_feedback_event: convenience wrapper to emit a phase4.feedback event from a
  feedback record matching PHASE_4_FEEDBACK_CAPTURE.schema.json

This module only builds dictionaries; it does not persist logs.
No raw canonical payload is stored in events; only request_id + payload_hash.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_phase4_event_log_entry(
    *,
    event_id: str,
    event_type: str,
    request_id: str,
    payload_hash: str,
    game_id: str,
    song_id: Optional[Any] = None,
    difficulty_label: Optional[str] = None,
    engine_mode: Optional[str] = None,
    session_id: Optional[str] = None,
    player_id_hash: Optional[str] = None,
    locale: Optional[str] = None,
    app_version: Optional[str] = None,
    model_bundle_version: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
    decision: Optional[Dict[str, Any]] = None,
    ui: Optional[Dict[str, Any]] = None,
    feedback: Optional[Dict[str, Any]] = None,
    outcome: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an event log record conforming to PHASE_4_EVENT_LOG.schema.json.

    Notes:
    - This helper builds the dict only (no persistence).
    - No raw canonical payload is stored, only payload_hash.
    """

    evt: Dict[str, Any] = {
        "event_id": str(event_id),
        "event_type": str(event_type),
        "event_timestamp": _utc_now_iso(),
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
    if feature_flags:
        evt["context"]["feature_flags"] = dict(feature_flags)

    # optional sections
    if decision:
        evt["decision"] = dict(decision)
    if ui:
        evt["ui"] = dict(ui)
    if feedback:
        evt["feedback"] = dict(feedback)
    if outcome:
        evt["outcome"] = dict(outcome)

    return evt


def build_phase4_feedback_event(
    *,
    event_id: str,
    feedback_record: Dict[str, Any],
    game_id: str,
    session_id: Optional[str] = None,
    app_version: Optional[str] = None,
    model_bundle_version: Optional[str] = None,
    feature_flags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience builder: convert a feedback capture record into a phase4.feedback event.

    Expects feedback_record to follow PHASE_4_FEEDBACK_CAPTURE.schema.json shape:
      {
        "target": {"request_id": ..., "payload_hash": ..., "event_id"?: ...},
        "signal": {"helpful": bool, "flagged"?: bool},
        "reason": {"reason_code"?: str, "comment"?: str}?,
        "context": {"song_id"?: ..., "difficulty_label"?: ..., "engine_mode"?: ..., "locale"?: ...}?,
        "privacy": {"player_id_hash"?: ...}?
      }

    This function maps it into PHASE_4_EVENT_LOG.schema.json "feedback" and "request" fields.
    """

    tgt = feedback_record.get("target") or {}
    sig = feedback_record.get("signal") or {}
    rea = feedback_record.get("reason") or {}
    ctx = feedback_record.get("context") or {}
    prv = feedback_record.get("privacy") or {}

    request_id = str(tgt.get("request_id") or "")
    payload_hash = str(tgt.get("payload_hash") or "")

    fb_block: Dict[str, Any] = {
        "helpful": bool(sig.get("helpful")),
    }
    if "flagged" in sig:
        fb_block["flagged"] = bool(sig.get("flagged"))
    if rea.get("reason_code"):
        fb_block["reason_code"] = str(rea.get("reason_code"))
    if rea.get("comment"):
        fb_block["comment"] = str(rea.get("comment"))

    return build_phase4_event_log_entry(
        event_id=event_id,
        event_type="phase4.feedback",
        request_id=request_id,
        payload_hash=payload_hash,
        game_id=game_id,
        song_id=ctx.get("song_id"),
        difficulty_label=ctx.get("difficulty_label"),
        engine_mode=ctx.get("engine_mode"),
        session_id=session_id,
        player_id_hash=prv.get("player_id_hash"),
        locale=ctx.get("locale"),
        app_version=app_version or ctx.get("app_version"),
        model_bundle_version=model_bundle_version,
        feature_flags=feature_flags,
        feedback=fb_block,
    )


__all__ = [
    "build_phase4_event_log_entry",
    "build_phase4_feedback_event",
]
