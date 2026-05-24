"""
Song Recommendation CI Test — Catalog Selector Window Widening

Invariant:
- Selector widens search window deterministically when no candidate is found
- Widening order is fixed
- Result must be reproducible

This test prevents accidental randomness or unstable fallback logic.
"""

from __future__ import annotations

import pytest


def _imports():
    try:
        from .song_recommendations.catalog_loader import load_catalog_from_artifacts
        from .song_recommendations.catalog_selector import (
            make_catalog_selector,
            SelectorConfig,
        )
        from .song_recommendations.song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, SelectorConfig, Target
    except Exception:
        from .catalog_loader import load_catalog_from_artifacts
        from .catalog_selector import make_catalog_selector, SelectorConfig
        from .song_rec_coordinator import Target
        return load_catalog_from_artifacts, make_catalog_selector, SelectorConfig, Target


def test_selector_window_widens_deterministically():
    load_catalog_from_artifacts, make_catalog_selector, SelectorConfig, Target = _imports()

    songs = {
        "songs": [
            {"song_id": "S_LOW", "name": "Low Song", "producer_id": "P1"},
            {"song_id": "S_HIGH", "name": "High Song", "producer_id": "P1"},
        ]
    }
    producers = {
        "producers": [
            {"producer_id": "P1", "name": "Producer", "avg_difficulty": 20}
        ]
    }
    difficulty = {
        "difficulty": [
            # Note: both songs are far away from target=10
            {"song_id": "S_LOW", "tier_id": "expert", "level": 1, "producer_id": "P1"},
            {"song_id": "S_HIGH", "tier_id": "expert", "level": 30, "producer_id": "P1"},
        ]
    }

    catalog = load_catalog_from_artifacts(
        game_id="proseka",
        songs_artifact=songs,
        producers_artifact=producers,
        difficulty_artifact=difficulty,
    )

    # Narrow initial window, deterministic widen steps
    config = SelectorConfig(
        window=2.0,
        widen_steps=(2.0, 5.0, 15.0, 50.0),
        top_producers=3,
    )

    selector = make_catalog_selector(catalog, config=config)

    target = Target(
        tier_id="expert",
        completion_id="clear",
        target_count=10,
    )

    chosen = selector(target, excluded_song_ids=set())

    assert chosen is not None, "Selector should eventually find a song via widening"
    # Closest by abs(level - target) = |1-10|=9 vs |30-10|=20
    assert chosen["song_id"] == "S_LOW"

    # Determinism check: run again
    chosen2 = selector(target, excluded_song_ids=set())
    assert chosen == chosen2, "Window widening result must be deterministic"