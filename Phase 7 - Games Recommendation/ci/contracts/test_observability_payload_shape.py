# test_observability_payload_shape.py
#
# Phase 7 CI — Observability Payload Contract
#
# Role:
# - Contract-level guardrail (NOT Wave 3)
# - Ensures observability payload shape is stable and serializable
# - Ensures non-blocking behavior even if sink fails
#
# Non-goals:
# - Does NOT validate metric values
# - Does NOT validate ranking or explanation quality
# - Does NOT depend on Phase 6 transport or infra

import pytest
import json
from datetime import datetime


def _import_observability():
    """
    Import observability primitives with strict expectation.
    This test MUST fail if observability layer disappears.
    """
    from rhythm_recommendation.phase7.observability import (  # type: ignore
        Phase7Observation,
        collect_observation,
    )
    return Phase7Observation, collect_observation


def _import_contract_item():
    from rhythm_recommendation.phase7.contracts.types import RecommendationItem  # type: ignore
    return RecommendationItem


def test_observability_payload_contract_and_serializability():
    Phase7Observation, collect_observation = _import_observability()
    RecommendationItem = _import_contract_item()

    items = [
        RecommendationItem(
            game_id="proseka",
            song_id="",
            score=0.8,
            rationale={},
        ),
        RecommendationItem(
            game_id="arcaea",
            song_id="",
            score=0.6,
            rationale={},
        ),
    ]

    payload = collect_observation(
        player_id="p1",
        locale="en",
        items=items,
        reason=None,
        sink=None,
    )

    # ---- Shape guarantee ----
    required_keys = {
        "player_id",
        "locale",
        "requested",
        "returned",
        "has_explanations",
        "avg_why_count",
        "distinct_game_count",
        "degraded",
        "reason",
        "occurred_at_iso",
    }
    assert required_keys == set(payload.keys())

    # ---- Type guarantees ----
    assert isinstance(payload["player_id"], str)
    assert isinstance(payload["locale"], str)
    assert isinstance(payload["requested"], int)
    assert isinstance(payload["returned"], int)
    assert isinstance(payload["has_explanations"], bool)
    assert payload["avg_why_count"] is None or isinstance(payload["avg_why_count"], (int, float))
    assert isinstance(payload["distinct_game_count"], int)
    assert isinstance(payload["degraded"], bool)
    assert payload["reason"] is None or isinstance(payload["reason"], str)
    assert isinstance(payload["occurred_at_iso"], str)

    # ---- RFC3339-like timestamp sanity (non-strict) ----
    datetime.fromisoformat(payload["occurred_at_iso"].replace("Z", "+00:00"))

    # ---- JSON serializability guarantee ----
    json.dumps(payload)


def test_observability_non_blocking_on_sink_failure():
    _, collect_observation = _import_observability()
    RecommendationItem = _import_contract_item()

    def failing_sink(_payload):
        raise RuntimeError("transport down")

    items = [
        RecommendationItem(
            game_id="proseka",
            song_id="",
            score=0.4,
            rationale={},
        )
    ]

    # Must not raise
    payload = collect_observation(
        player_id="p2",
        locale="zh-HK",
        items=items,
        reason="sink_failure_test",
        sink=failing_sink,
    )

    assert payload["degraded"] is True
    assert payload["reason"] == "sink_failure_test"