"""
Score Diversity (CI) — Phase 7 (registry-driven)

Purpose:
- ensure ranking does not collapse into identical scores

Non-semantic:
- does NOT enforce quality
- only checks non-degenerate output
"""

from ranking.ranker import DeterministicRanker
from registry.registry import load_games_registry


def _rank_scores():
    registry = load_games_registry("games.json")

    candidate_ids = [
        g.game_id
        for g in registry.games
        if getattr(g, "overall_status", None) in ("enabled", "anchor")
    ]

    ranker = DeterministicRanker()

    items = ranker.rank(
        candidate_game_ids=candidate_ids,
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
        game_profiles={},
    )

    scores = []

    for item in items:
        s = getattr(item, "score", None)
        if s is None and isinstance(item, dict):
            s = item.get("score")

        if isinstance(s, (int, float)):
            scores.append(float(s))

    return scores


def test_score_diversity_not_degenerate():
    scores = _rank_scores()

    # empty is allowed (CI-level safeguard)
    if not scores:
        return

    unique_scores = set(scores)

    # ✅ key rule: must not collapse into single value
    assert len(unique_scores) > 1, "All recommendation scores are identical"
