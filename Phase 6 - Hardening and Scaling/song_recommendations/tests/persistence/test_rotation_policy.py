"""
Song Recommendation CI Test — Rotation Policy (Phase 6 module-level)

Guarantee:
- action=refresh -> no persistence plan
- action=save -> persistence plan exists
- rotation never deletes bookmarked items
- deletion order deterministic (oldest first, stable tie-break)
"""

from __future__ import annotations

import pytest


def _imports():
    try:
        from phase6.song_recommendation.request_normalizer import normalize_song_recommendation_request
        from phase6.song_recommendation.persistence_policy import compute_persistence_plan
        return normalize_song_recommendation_request, compute_persistence_plan
    except Exception:
        from request_normalizer import normalize_song_recommendation_request
        from persistence_policy import compute_persistence_plan
        return normalize_song_recommendation_request, compute_persistence_plan


def test_refresh_has_no_persistence_plan():
    normalize_song_recommendation_request, compute_persistence_plan = _imports()

    req = normalize_song_recommendation_request(
        {
            "game_id": "proseka",
            "mode": "songs",
            "action": "refresh",
            "submission": {"difficulty_progress": {"tiers": [{"tier_id": "expert", "counts": {"clear": 1}}]}},
            "recent_recommendations": [],
        }
    )

    plan = compute_persistence_plan(req, items=[{"song_id": "S1"}], max_history=10)
    assert plan.did_save is False
    assert plan.create_records == []
    assert plan.delete_ids == []
    assert plan.delete_count == 0


def test_save_rotation_deletes_oldest_non_bookmarked_only():
    normalize_song_recommendation_request, compute_persistence_plan = _imports()

    req = normalize_song_recommendation_request(
        {
            "game_id": "proseka",
            "mode": "songs",
            "action": "save",
            "player_id_hash": "p123",
            "submission": {"difficulty_progress": {"tiers": [{"tier_id": "expert", "counts": {"clear": 5}}]}},
            "recent_recommendations": [
                {"song_id": "A", "bookmarked": False, "created_at": "2026-01-01T00:00:00Z", "record_id": "R-old"},
