"""
Song Recommendation CI Test — Catalog Selector Multi-Tier Safety

Invariant:
- Selector MUST only select songs from the requested tier_id
- No cross-tier leakage is allowed
"""

from __future__ import annotations

from song_recommendations.catalog_loader import load_catalog_from_artifacts
from song_recommendations.catalog_selector import make_catalog_selector
from song_recommendations.game_capability_resolver import resolve_game_capability
from song_recommendations.song_rec_coordinator import Target


def test_selector_does_not_cross_tiers():
    cap = resolve_game_capability("proseka")
    catalog = load_catalog_from_artifacts(game_id="proseka", capability=cap)
    selector = make_catalog_selector(catalog)

    if len(cap.difficulty_tiers) < 2:
        # Can't test cross-tier without at least two tiers
        return

    target_tier = cap.difficulty_tiers[0]
    other_tier = cap.difficulty_tiers[1]

    target = Target(tier_id=target_tier, completion_id=cap.completion_ladder[0], target_count=1)
    chosen = selector(target, set())

    if chosen is None:
        return

    # Require chosen item to belong to the target tier
    assert chosen.get("tier_id") != other_tier
    assert chosen.get("tier_id") == target_tier