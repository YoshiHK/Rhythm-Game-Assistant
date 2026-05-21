"""
Phase 7 CI — Ranker Regression Stability (registry-driven)

Ensures:
- ordering stability
- score stability
"""

from ranking.ranker import DeterministicRanker
from registry.registry import load_games_registry


def _run_scenario():
    registry = load_games_registry("games.json")

    candidate_ids = [
        g.game_id
        for g in registry.games
        if getattr(g, "overall_status", None) in ("enabled", "anchor")
    ]

    ranker = DeterministicRanker()

    return ranker.rank(
        candidate_game_ids=candidate_ids,
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
        game_profiles={},
    )


def test_ranker_order_is_stable():
    out1 = _run_scenario()
    out2 = _run_scenario()

    assert out1 == out2


def test_ranker_scores_are_stable():
    out1 = _run_scenario()
    out2 = _run_scenario()

    def extract_scores(out):
        scores = []
        for item in out:
            s = getattr(item, "score", None)
            if s is None and isinstance(item, dict):
                s = item.get("score")

            if isinstance(s, (int, float)):
                scores.append(float(s))
        return scores

    assert extract_scores(out1) == extract_scores(out2)