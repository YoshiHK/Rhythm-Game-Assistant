"""
Song Recommendation CI Test — Catalog Selector Determinism

Guarantee:
- With identical catalog + identical target + identical exclusions,
  selector returns identical output (deterministic).
"""

from __future__ import annotations

from song_recommendations.catalog.catalog_loader import load_catalog_from_artifacts
from song_recommendations.catalog.catalog_selector import make_catalog_selector
from song_recommendations.game_capability_resolver import resolve_game_capability
from song_recommendations.song_rec_coordinator import Target


def test_selector_is_deterministic():
    cap = resolve_game_capability("proseka")
    catalog = load_catalog_from_artifacts(game_id="proseka", capability=cap)

    selector = make_catalog_selector(catalog)

    target = Target(tier_id=cap.difficulty_tiers[0], completion_id=cap.completion_ladder[0], target_count=1)
    excluded = set()

    out1 = selector(target, excluded)
    out2 = selector(target, excluded)

    assert out1 == out2
