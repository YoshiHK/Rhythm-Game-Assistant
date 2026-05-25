"""
Song Recommendation CI Test — Determinism (Phase 6 module-level)

Guarantee:
- Same normalized request -> same recommendation set (given deterministic selector)
- No randomness allowed in selection tie-break

Non-goals:
- Does not judge recommendation quality
"""

from __future__ import annotations

import pytest

from song_recommendations.request_normalizer import normalize_song_recommendation_request
from song_recommendations.game_capability_resolver import resolve_game_capability
from song_recommendations.song_rec_coordinator import generate_recommendation_items


def _deterministic_selector_factory():
    """
    Deterministic selector stub:
    returns a stable song dict derived from (tier_id, completion_id).
    Excluded ids are respected.
    """
    def selector(target, excluded_song_ids):
        song_id = f"{target.tier_id}-{target.completion_id}-seed"
        if song_id in excluded_song_ids:
            return None
        return {
            "song_id": song_id,
            "title": song_id,
            "tier_id": target.tier_id,
            "target_completion": target.completion_id,
        }
    return selector



def test_song_rec_is_deterministic_for_identical_input():
    payload = {
        "mode": "songs",
        "game_id": "proseka",
        "locale": "en",
        "max_items": 3,
        "action": "refresh",
        "player_id_hash": "p1",
        "submission": {
            "difficulty_progress": {
                "tiers": [
                    {"tier_id": "Expert", "counts": {"Clear": 10, "FC": 3, "AP": 1}}
                ]
            }
        },
        "recent_recommendations": [],
        "client": {"platform": "ci"},
    }


    req = normalize_song_recommendation_request(payload)
    cap = resolve_game_capability(req.game_id)

    selector = _deterministic_selector_factory()

    out1, diag1 = generate_recommendation_items(req, cap, selector=selector)
    out2, diag2 = generate_recommendation_items(req, cap, selector=selector)

    assert out1 == out2
    assert diag1 == diag2
    
