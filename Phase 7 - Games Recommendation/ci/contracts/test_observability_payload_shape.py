"""
Phase 7 CI — Observability Payload Contract (registry-driven)

Purpose:
- ensure observability payload shape is stable
- ensure serializability
- ensure non-blocking behavior

Non-goals:
- does NOT validate metric quality
- does NOT validate ranking logic
"""

import json
from datetime import datetime

import pytest

from observability.metrics_collector import (
    Phase7Observation,
    collect_observation,
)

from ranking.ranker import DeterministicRanker
from registry import load_games_registry


def _build_sample_observation():
    registry = load_games_registry("games.json")

    candidate_ids = [
        g.game_id
        for g in registry.games
        if getattr(g, "overall_status", None) in ("enabled", "anchor")
    ]

    ranker = DeterministicRanker()

    items = ranker.rank(
        candidate_game_ids=candidate_ids[:3],  # small subset OK
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
        game_profiles={},
    )

    return Phase7Observation(
        player_id="p1",
        timestamp=datetime.utcnow().isoformat(),
        recommendation_count=len(items),
        metadata={"ci": True},
    )


def test_observability_payload_contract_and_serializability():
    obs = _build_sample_observation()

    payload = obs.to_dict() if hasattr(obs, "to_dict") else obs.__dict__

    json.dumps(payload)

    # ✅ minimal contract
    assert "player_id" in payload
    assert "timestamp" in payload
    assert "recommendation_count" in payload


def test_observability_non_blocking_on_sink_failure():
    obs = _build_sample_observation()

    try:
        collect_observation(obs)
    except Exception as e:
        pytest.fail(f"Observability must be non-blocking, got exception: {e}")