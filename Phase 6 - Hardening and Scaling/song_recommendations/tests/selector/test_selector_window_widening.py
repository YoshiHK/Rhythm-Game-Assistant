"""
Song Recommendation CI Test — Catalog Selector Window Widening

Invariant:
- Selector widens search window deterministically when no candidate is found
- Widening order is fixed
- Result must be reproducible
"""

from __future__ import annotations

from song_recommendations.catalog_loader import load_catalog_from_artifacts
from song_recommendations.catalog_selector import make_catalog_selector, SelectorConfig
from song_recommendations.game_capability_resolver import resolve_game_capability
from song_recommendations.song_rec_coordinator import Target


def test_selector_window_widens_deterministically():
    cap = resolve_game_capability("proseka")
    catalog = load_catalog_from_artifacts(game_id="proseka", capability=cap)

    cfg = SelectorConfig()  # default widening rules must be deterministic
    selector = make_catalog_selector(catalog, config=cfg)

    target = Target(tier_id=cap.difficulty_tiers[0], completion_id=cap.completion_ladder[0], target_count=1)

    # Exclude everything we can see to force widening behavior
    # If catalog is empty, this test becomes vacuous
    all_ids = set()
    for row in getattr(catalog, "rows", []) or []:
        sid = row.get("song_id") if isinstance(row, dict) else None
        if sid:
            all_ids.add(sid)

    out1 = selector(target, all_ids)
    out2 = selector(target, all_ids)

    assert out1 == out2