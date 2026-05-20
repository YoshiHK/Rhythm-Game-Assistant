# test_feedback_payload_shape.py
#
# Phase 7 CI — Feedback Payload Contract
#
# Role:
# - Contract-level guardrail (NOT Wave 3)
# - Ensures feedback event payload shape is stable
# - Ensures non-blocking behavior when sink fails
#
# Non-goals:
# - Does NOT validate learning behavior
# - Does NOT validate Phase  or persistence# - Does NOT validate Phase 5 ingestion

import pytest
import json
from datetime import datetime


def _import_feedback():
    from feedback.feedback_forwarder import (  # type: ignore
        Phase7FeedbackEvent,
        FeedbackAction,
        emit_feedback_event,
    )
    return Phase7FeedbackEvent, FeedbackAction, emit_feedback_event


def test_feedback_payload_contract_and_serializability():
    Phase7FeedbackEvent, FeedbackAction, emit_feedback_event = _import_feedback()

    payload = emit_feedback_event(
        player_id="p1",
        game_id="proseka",
        action=FeedbackAction.ACCEPT,
        locale="en",
        recommendation_rank=1,
        sink=None,
    )

    # ---- Shape guarantee ----
    required_keys = {
        "player_id",
        "game_id",
        "action",
        "locale",
        "recommendation_rank",
        "source",
        "occurred_at_iso",
    }
    assert required_keys == set(payload.keys())

    # ---- Type guarantees ----
    assert isinstance(payload["player_id"], str)
    assert isinstance(payload["game_id"], str)
    assert isinstance(payload["action"], str)
    assert isinstance(payload["locale"], str)
    assert isinstance(payload["recommendation_rank"], int)
    assert payload["source"] == "phase7"
    assert isinstance(payload["occurred_at_iso"], str)

    # ---- Enum guarantee ----
    assert payload["action"] in {a.value for a in FeedbackAction}

    # ---- Timestamp sanity ----
    datetime.fromisoformat(payload["occurred_at_iso"].replace("Z", "+00:00"))

    # ---- JSON serializability guarantee ----
    json.dumps(payload)


def test_feedback_non_blocking_on_sink_failure():
    _, FeedbackAction, emit_feedback_event = _import_feedback()

    def failing_sink(_payload):
        raise RuntimeError("event bus down")

    # Must not raise
    payload = emit_feedback_event(
        player_id="p2",
        game_id="arcaea",
        action=FeedbackAction.DISMISS,
        locale="zh-HK",
        recommendation_rank=2,
        sink=failing_sink,
    )

    assert payload["action"] == FeedbackAction.DISMISS.value
    assert payload["player_id"] == "p2"
    assert payload["game_id"] == "arcaea"
