"""
Phase 7 CI — Scoring Availability (registry-driven)

Ensures:
- every recommendable game is scorable
- scores are finite numbers
"""

import math

from ranking.ranker import DeterministicRanker
from registry.registry import load_games_registry


def test_scoring_availability_for_recommendable_games():
    registry = load_games_registry("games.json")

    candidate_ids = [
        g.game_id
        for g in registry.games
        if getattr(g, "overall_status", None) in ("enabled", "anchor")
    ]

    assert candidate_ids, "No recommendable games found"

    ranker = DeterministicRanker()

    out = ranker.rank(
        candidate_game_ids=candidate_ids,
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
        game_profiles={},
    )

    assert out, "Ranker returned no items"

    for item in out:
        score = getattr(item, "score", None)

        if score is None and isinstance(item, dict):
            score = item.get("score")

        assert isinstance(score, (int, float)), "Score must be numeric"
        assert math.isfinite(score), "Score must be finite"