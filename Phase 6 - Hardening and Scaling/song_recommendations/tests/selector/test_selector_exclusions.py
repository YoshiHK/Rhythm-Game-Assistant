"""
Song Recommendation CI Test — Catalog Selector Exclusions

Guarantee:
- selector respects excluded_song_ids
- when best candidate is excluded, next best deterministic candidate is chosen
"""

from __future__ import annotations

import pytest

def _imports():
    try:
        from phase6.song_recommendation.catalog_loader import load_catalog_from_artifacts
        from phase6.song_recommendation.catalog_selector import make_catalog_selector
        from phase6.song_recommendation.song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, Target
    except Exception:
        from catalog_loader import load_catalog_from_artifacts
        from catalog_selector import make_catalog_selector
        from song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, Target


def test_selector_respects_exclusions():
    load_catalog_from_artifacts, make_catalog_selector, Target = _imports()

    songs = {
        "songs": [
            {"song_id": "S1", "name": "Song 1", "producer_id": "P1"},
            {"song_id": "S2", "name": "Song 2", "producer_id": "P1"},
        ]
    }
    producers = {"producers": [{"producer_id": "P1", "name": "Producer 1", "avg_difficulty": 10}]}
    difficulty = {
        "difficulty": [
            {"song_id": "S1", "tier_id": "expert", "level": 10, "producer_id": "P1"},
            {"song_id": "S2", "tier_id": "expert", "level": 11, "producer_id": "P1"},
        ]
    }

    catalog = load_catalog_from_artifacts(
        game_id="proseka",
        songs_artifact=songs,
        producers_artifact=producers,
        difficulty_artifact=difficulty,
    )

    selector = make_catalog_selector(catalog)

    target = Target(tier_id="expert", completion_id="clear", target_count=10)

    # S1 is the closest (level=10). Exclude it, should pick S2 deterministically.
    excluded = {"S1"}
    chosen = selector(target, excluded)

    assert chosen is not None
    assert chosen["song_id"] == "S2"