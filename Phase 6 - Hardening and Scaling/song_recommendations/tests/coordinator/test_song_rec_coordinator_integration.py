"""
Song Recommendation CI Test — Coordinator Integration (Phase 6)

Purpose:
End-to-end integration test for Phase 6 song recommendation wiring:
normalize request
-> resolve game capability (difficulty tiers + completion ladder)
-> coordinator generates 3-in-a-group targets (AP/FC/Clear logical types)
-> persistence plan (save/rotation)
-> response shaping (stable set_id + JSON serializable)

Invariants enforced:
- Deterministic output for identical inputs
- Exclusions respected (song_id-based)
- Multi-game safe: no hardcoded Proseka-only assumptions in request schema
"""

from __future__ import annotations

import json

from song_recommendations.request_normalizer import normalize_song_recommendation_request
from song_recommendations.game_capability_resolver import resolve_game_capability
from song_recommendations.song_rec_coordinator import generate_recommendation_items
from song_recommendations.persistence_policy import compute_persistence_plan
from song_recommendations.response_shaper import shape_song_recommendation_response


def _deterministic_selector(target, excluded_song_ids):
    # Stable, deterministic song_id per target; respects exclusions.
    song_id = f"{target.tier_id}-{target.completion_id}-seed"
    if song_id in excluded_song_ids:
        return None
    return {
        "song_id": song_id,
        "title": song_id,
        "tier_id": target.tier_id,
        "target_completion": target.completion_id,
    }


def test_song_rec_integration_is_deterministic_and_respects_exclusions():
    payload = {
        "mode": "songs",
        "game_id": "proseka",
        "locale": "en",
        "max_items": 3,
        "action": "save",
        "player_id_hash": "p1",
        "submission": {
            "difficulty_progress": {  # ✅ FIX HERE
                "tiers": [
                    {"tier_id": "Expert", "counts": {"Clear": 10, "FC": 3, "AP": 1}},
                ]
            }
        },
        "recent_recommendations": [
            {
                "song_id": "expert-ap-seed",
                "bookmarked": False,
                "created_at": None,
                "record_id": "r1",
            },
        ],
        "client": {"platform": "ci"},
    }

    req = normalize_song_recommendation_request(payload)
    cap = resolve_game_capability(req.game_id)

    items1, diag1 = generate_recommendation_items(req, cap, selector=_deterministic_selector)
    items2, diag2 = generate_recommendation_items(req, cap, selector=_deterministic_selector)

    assert items1 == items2
    assert diag1 == diag2

    # Exclusion respected
    ids = [it.get("song_id") for it in items1 if isinstance(it, dict)]
    assert "expert-ap-seed" not in ids

    # Persistence plan is deterministic
    plan1 = compute_persistence_plan(req, items1)
    plan2 = compute_persistence_plan(req, items1)
    assert plan1 == plan2

    # Response shaper is JSON-serializable and deterministic set_id
    resp1 = shape_song_recommendation_response(req, items=items1, persistence=plan1, diagnostics=diag1)
    resp2 = shape_song_recommendation_response(req, items=items1, persistence=plan1, diagnostics=diag1)

    assert resp1 == resp2
    json.dumps(resp1)  # must not raise
    assert "recommendation_set" in resp1
    assert "set_id" in resp1["recommendation_set"]