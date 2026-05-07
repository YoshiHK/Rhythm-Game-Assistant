from __future__ import annotations

"""
feedback_capture.py

Phase 4 — Events Layer: Feedback Capture record builder (append-only)

Builds dictionaries that conform to:
- PHASE_4_FEEDBACK_CAPTURE.schema.json

Hard constraints:
- No persistence
- No PII (player_id must be hashed upstream)
- No raw canonical payload stored (only request_id + payload_hash)
- Feedback must not affect runtime outputs directly
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_phase4_feedback_capture_record(
    *,
    feedback_id: str,
    request_id: str,
    payload_hash: str,
    helpful: bool,
    feedback_timestamp: Optional[str] = None,
    # optional signal fields
    flagged: Optional[bool] = None,
    # optional reason fields
    reason_code: Optional[str] = None,
    comment: Optional[str] = None,
    # optional linkage
    event_id: Optional[str] = None,
    # optional context block (schema supports these)
    game_id: Optional[str] = None,
    song_id: Optional[Any] = None,
    difficulty_label: Optional[str] = None,
    engine_mode: Optional[str] = None,  # deterministic|personalized|debug
    locale: Optional[str] = None,
    app_version: Optional[str] = None,
    # optional privacy block (schema supports these)
    player_id_hash: Optional[str] = None,
    consent_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a feedback capture record conforming to PHASE_4_FEEDBACK_CAPTURE.schema.json.

    Required:
    - feedback_id
    - feedback_timestamp
    - target.request_id, target.payload_hash
    - signal.helpful

    Optional blocks are included only when provided.
    """

    rec: Dict[str, Any] = {
        "feedback_id": str(feedback_id),
        "feedback_timestamp": str(feedback_timestamp or _utc_now_iso()),
        "target": {
            "request_id": str(request_id),
            "payload_hash": str(payload_hash),
        },
        "signal": {
            "helpful": bool(helpful),
        },
    }

    if event_id:
        rec["target"]["event_id"] = str(event_id)

    if flagged is not None:
        rec["signal"]["flagged"] = bool(flagged)

    # reason block is optional
    if reason_code is not None or comment:
        reason: Dict[str, Any] = {}
        if reason_code is not None:
            reason["reason_code"] = str(reason_code)
        if comment:
            reason["comment"] = str(comment)
        rec["reason"] = reason

    # context block is optional
    context: Dict[str, Any] = {}
    if game_id is not None:
        context["game_id"] = str(game_id)
    if song_id is not None:
        context["song_id"] = song_id
    if difficulty_label is not None:
        context["difficulty_label"] = str(difficulty_label)
    if engine_mode is not None:
        context["engine_mode"] = str(engine_mode)
    if locale is not None:
        context["locale"] = str(locale)
    if app_version is not None:
        context["app_version"] = str(app_version)
    if context:
        rec["context"] = context

    # privacy block is optional
    privacy: Dict[str, Any] = {}
    if player_id_hash is not None:
        privacy["player_id_hash"] = str(player_id_hash)
    if consent_version is not None:
        privacy["consent_version"] = str(consent_version)
    if privacy:
        rec["privacy"] = privacy

    return rec


__all__ = ["build_phase4_feedback_capture_record"]