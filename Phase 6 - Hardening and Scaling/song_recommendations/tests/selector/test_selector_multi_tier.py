"""
Song Recommendation CI Test — Catalog Selector Multi-Tier Safety

Invariant:
- Selector MUST only select songs from the requested tier_id
- No cross-tier leakage is allowed (e.g. Expert target must not return Master song)

This test protects multi-game and multi-difficulty correctness.
"""

from __future__ import annotations

import pytest


def _imports():
    try:
        from .song_recommendations.catalog_loader import load_catalog_from_artifacts
        from .song_recommendations.catalog_selector import make_catalog_selector
        from .song_recommendations.song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, Target
    except Exception:
        from .catalog_loader import load_catalog_from_artifacts
        from .catalog_selector import make_catalog_selector
        from .song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, Target


def test_selector_does_not_cross_tiers():
    load_catalog_from_artifacts, make_catalog_selector, Target = _imports()

    # Two tiers with overlapping metrics — this is the dangerous case
    songs = {
        "songs": [
            {"song_id": "E1", "name": "Expert Song", "producer_id": "P1"},
            {"song_id": "M1", "name": "Master Song", "producer_id": "P1"},
        ]
    }
    producers = {
        "producers": [
            {"producer_id": "P1", "name": "Producer", "avg_difficulty": 10}
        ]
    }
    difficulty = {
        "difficulty": [
            # Expert tier
            {"song_id": "E1", "tier_id": "expert", "level": 10, "producer_id": "P1"},
            # Master tier — same metric, must NOT be chosen for expert target
            {"song_id": "M1", "tier_id": "master", "level": 10, "producer_id": "P1"},
        ]
    }

    catalog = load_catalog_from_artifacts(
        game_id="proseka",
        songs_artifact=songs,
        producers_artifact=producers,
        difficulty_artifact=difficulty,
    )

    selector = make_catalog_selector(catalog)

    # Target explicitly asks for expert tier
    target = Target(
        tier_id="expert",
        completion_id="clear",
        target_count=10,
    )

    chosen = selector(target, excluded_song_ids=set())

    assert chosen is not None, "Selector should find a candidate"
    assert chosen["song_id"] == "E1", "Selector must not cross tiers"
    assert chosen["difficulty"] == "expert"