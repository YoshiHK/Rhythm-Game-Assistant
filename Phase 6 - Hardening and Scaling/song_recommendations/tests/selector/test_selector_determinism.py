"""
Song Recommendation CI Test — Catalog Selector Determinism

Guarantee:
- With identical catalog + identical target + identical exclusions,
  selector returns identical output (deterministic).
"""

from __future__ import annotations

import pytest

# Flexible imports: package or flat
def _imports():
    try:
        from .song_recommendations.catalog_loader import load_catalog_from_artifacts
        from .song_recommendations.catalog_selector import make_catalog_selector
        from .song_recommendations.game_capability_resolver import resolve_game_capability
        from .song_recommendations.song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, resolve_game_capability, Target
    except Exception:
        from .catalog_loader import load_catalog_from_artifacts
        from .catalog_selector import make_catalog_selector
        from .game_capability_resolver import resolve_game_capability
        from .song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, resolve_game_capability, Target


def test_selector_is_deterministic():
    load_catalog_from_artifacts, make_catalog_selector, resolve_game_capability, Target = _imports()

    # Minimal in-memory artifacts
    songs = {
        "songs": [
            {"song_id": "S1", "name": "Song 1", "producer_id": "P1"},
            {"song_id": "S2", "name": "Song 2", "producer_id": "P1"},
            {"song_id": "S3", "name": "Song 3", "producer_id": "P2"},
        ]
    }
    producers = {
        "producers": [
            {"producer_id": "P1", "name": "Producer 1", "avg_difficulty": 10},
            {"producer_id": "P2", "name": "Producer 2", "avg_difficulty": 12},
        ]
    }
    difficulty = {
        "difficulty": [
            {"song_id": "S1", "tier_id": "expert", "level": 9, "producer_id": "P1"},
            {"song_id": "S2", "tier_id": "expert", "level": 10, "producer_id": "P1"},
            {"song_id": "S3", "tier_id": "expert", "level": 12, "producer_id": "P2"},
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
    excluded = set()

    a = selector(target, excluded)
    b = selector(target, excluded)

    assert a == b
    assert a is not None
    assert a["song_id"] in {"S1", "S2", "S3"}