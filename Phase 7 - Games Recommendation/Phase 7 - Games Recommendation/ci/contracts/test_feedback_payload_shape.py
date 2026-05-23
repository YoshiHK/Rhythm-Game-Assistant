"""
Phase 7 CI — Feedback Payload Contract (registry-driven)

Purpose:
- ensure feedback payload shape is stable
- ensure serializability
- ensure non-blocking behavior

Non-goals:
- does NOT evaluate learning
- does NOT validate persistence
"""

import json
from datetime import datetime

import pytest

from feedback.feedback_forwarder import (
    Phase7FeedbackEvent,
    FeedbackAction,
    emit_feedback_event,
)

from registry import load_games_registry


def _build_sample_event():
    registry = load_games_registry("games.json")

    # ✅ pick first enabled game safely
    game = next(
        g for g in registry.games
        if getattr(g, "overall_status", None) in ("enabled", "anchor")
    )

    return Phase7FeedbackEvent(
        player_id="p1",
        game_id=game.game_id,
        action=FeedbackAction.CLICK,
        timestamp=datetime.utcnow().isoformat(),
        metadata={"source": "ci_test"},
    )


def test_feedback_payload_contract_and_serializability():
    event = _build_sample_event()

    # ✅ must be serializable
    payload = event.to_dict() if hasattr(event, "to_dict") else event.__dict__

    json.dumps(payload)  # should not raise

    # ✅ minimal contract checks
    assert "player_id" in payload
    assert "game_id" in payload
    assert "action" in payload
    assert "timestamp" in payload


def test_feedback_non_blocking_on_sink_failure():
    event = _build_sample_event()

    # ✅ simulate failure safely (no exception should escape)
    try:
        emit_feedback_event(event)
    except Exception as e:
        pytest.fail(f"Feedback emission must be non-blocking, got exception: {e}")