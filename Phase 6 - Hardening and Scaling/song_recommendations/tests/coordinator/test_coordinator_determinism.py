"""
Song Recommendation CI Test — Determinism (Phase 6 module-level)

Guarantee:
- Same normalized request -> same recommendation set (given deterministic selector)
- No randomness allowed in selection tie-break

Non-goals:
- Does not judge recommendation quality
"""

from __future__ import annotations

import json

import pytest


def _imports():
    """
    Support both flat imports (same folder) and package imports.
    Adjust these paths if you place modules under a package.
    """
    try:
        from .song_recommendations.request_normalizer import normalize_song_recommendation_request
        from .song_recommendations.game_capability_resolver import resolve_game_capability
        from .song_recommendations.song_rec_coordinator import generate_recommendation_items
        return normalize_song_recommendation_request, resolve_game_capability, generate_recommendation_items
    except Exception:
        from .request_normalizer import normalize_song_recommendation_request
        from .game_capability_resolver import resolve_game_capability
        from .song_rec_coordinator import generate_recommendation_items
        return normalize_song_recommendation_request, resolve_game_capability, generate_recommendation_items


def test_song_rec_is_deterministic_for_identical_input():
    normalize_song_recommendation_request, resolve_game_capability, generate_recommendation_items = _imports()

    payload = {
        "game_id": "proseka",
        "mode": "songs",
        "locale": "en-US",
        "max_items": 3,
        "action": "refresh",
        "player_id_hash": "p123",
        "submission": {
            "difficulty_progress": {
                "tiers": [
                    {"tier_id": "expert", "counts": {"clear": 30, "fc": 12, "ap": 4}},
                    {"tier_id": "master", "counts": {"clear": 10, "fc": 2, "ap": 0}},
                ]
            }
        },
        "recent_recommendations": [{"song_id": "S-OLD", "bookmarked": False, "record_id": "R1"}],
        "client": {"source": "pytest"},
    }

    req = normalize_song_recommendation_request(payload)
    cap = resolve_game_capability(req.game_id)

    # Deterministic selector stub:
    # - chooses a song_id purely from target fields (tier_id, completion_id, target_count)
    # - respects exclusions deterministically
    def selector(target, excluded):
        base = f"{target.tier_id}:{target.completion_id}:{target.target_count}"
        sid = "S-" + str(abs(hash(base)) % 10000)
        if sid in excluded:
            sid = "S-" + str((abs(hash(base)) + 1) % 10000)
        return {
            "song_id": sid,
            "song_name": f"Song {sid}",
            "producer_name": "Producer X",
            "difficulty": target.tier_id,
            "level": float(target.target_count),  # deterministic placeholder
            "rationale": {"summary": "test", "why": ["deterministic"]},
        }

    items1, diag1 = generate_recommendation_items(req, cap, selector=selector)
