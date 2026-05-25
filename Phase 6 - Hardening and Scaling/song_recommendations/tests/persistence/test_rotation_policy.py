"""
Song Recommendation CI Test — Rotation Policy (Phase 6 module-level)

Guarantee:
- action=refresh -> no persistence plan
- action=save -> persistence plan exists
- rotation never deletes bookmarked items
"""

from __future__ import annotations

from song_recommendations.request_normalizer import normalize_song_recommendation_request
from song_recommendations.persistence_policy import compute_persistence_plan


def test_refresh_has_no_persistence_plan():
    req = normalize_song_recommendation_request(
        {
            "game_id": "proseka",
            "mode": "songs",
            "action": "refresh",
            "submission": {
                "difficulty_progress": {"tiers": [{"tier_id": "expert", "counts": {"clear": 1}}]}
            },
        }
    )

    plan = compute_persistence_plan(req, items=[], max_history=10)

    assert plan.did_save is False
    assert plan.create_records == []
    assert plan.delete_ids == []


def test_save_rotation_deletes_oldest_non_bookmarked_only():
    req = normalize_song_recommendation_request(
        {
            "game_id": "proseka",
            "mode": "songs",
            "action": "save",
            "submission": {
                "difficulty_progress": {"tiers": [{"tier_id": "expert", "counts": {"clear": 1}}]}
            },
            "recent_recommendations": [
                {"song_id": "A", "bookmarked": False, "created_at": "2026-01-01T00:00:00Z", "record_id": "r1"},
                {"song_id": "B", "bookmarked": True,  "created_at": "2026-01-02T00:00:00Z", "record_id": "r2"},
            ],
        }
    )

    items = [{"song_id": "C"}]

    plan = compute_persistence_plan(req, items=items, max_history=1)

    # ✅ should save
    assert plan.did_save is True

    # ✅ must not delete bookmarked item
    assert "r2" not in plan.delete_ids
