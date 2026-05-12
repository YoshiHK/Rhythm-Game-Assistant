"""
Song Recommendation CI Test — Response Shaper Contract
Ensures response is stable, structured, and JSON-serializable.
"""

from __future__ import annotations

import json

import pytest


def _imports():
    try:
        from phase6.song_recommendation.request_normalizer import normalize_song_recommendation_request
        from phase6.song_recommendation.persistence_policy import compute_persistence_plan
        from phase6.song_recommendation.response_shaper import shape_song_recommendation_response
        return normalize_song_recommendation_request, compute_persistence_plan, shape_song_recommendation_response
    except Exception:
        from request_normalizer import normalize_song_recommendation_request
        from persistence_policy import compute_persistence_plan
        from response_shaper import shape_song_recommendation_response
        return normalize_song_recommendation_request, compute_persistence_plan, shape_song_recommendation_response


def test_response_is_json_serializable_and_has_set_id():
    normalize_song_recommendation_request, compute_persistence_plan, shape_song_recommendation_response = _imports()

    req = normalize_song_recommendation_request(
        {
            "game_id": "proseka",
            "mode": "songs",
            "action": "save",
            "submission": {"difficulty_progress": {"tiers": [{"tier_id": "expert", "counts": {"clear": 3}}]}},
            "recent_recommendations": [],
        }
    )

    items = [
        {
            "song_id": "S1",
            "song_name": "Song 1",
            "producer_name": "P",
            "difficulty": "expert",
            "level": 10.0,
            "recommendation_type": "Clear",
            "rationale": {"summary": "x", "why": ["y"]},
        }
    ]

    plan = compute_persistence_plan(req, items=items, max_history=10)
    resp = shape_song_recommendation_response(req, items=items, persistence=plan, diagnostics={"deterministic": True})

    assert resp["mode"] == "songs"
    assert "recommendation_set" in resp
    assert isinstance(resp["recommendation_set"]["set_id"], str)
    json.dumps(resp, ensure_ascii=False)