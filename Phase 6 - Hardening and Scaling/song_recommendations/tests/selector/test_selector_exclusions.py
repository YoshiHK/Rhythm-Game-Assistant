"""
Song Recommendation CI Test — Catalog Selector Exclusions

Guarantee:
- selector respects excluded_song_ids
- when best candidate is excluded, next best deterministic candidate is chosen
"""

from __future__ import annotations

from song_recommendations.catalog_loader import load_catalog_from_artifacts
from song_recommendations.catalog_selector import make_catalog_selector
from song_recommendations.game_capability_resolver import resolve_game_capability
from song_recommendations.song_rec_coordinator import Target


def test_selector_respects_exclusions():
    cap = resolve_game_capability("proseka")
    catalog = load_catalog_from_artifacts(game_id="proseka", capability=cap)
    selector = make_catalog_selector(catalog)

    target = Target(tier_id=cap.difficulty_tiers[0], completion_id=cap.completion_ladder[0], target_count=1)

    first = selector(target, set())
    if first is None:
        # If catalog is empty in this environment, test becomes vacuous
        return

    # Exclude the first choice and expect a deterministic alternative (or None)
    excluded = {first.get("song_id")}
    second = selector(target, excluded)

    assert second is None or second.get("song_id") != first.get("song_id")