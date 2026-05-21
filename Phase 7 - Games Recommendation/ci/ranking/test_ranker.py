"""
Phase 7 CI — Ranker Core Behavior (registry-driven)

Non-semantic:
- does NOT evaluate ranking quality
- only ensures safe & deterministic behavior
"""

from ranking.ranker import DeterministicRanker
from registry import load_games_registry


def _run_ranker():
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


def test_ranker_is_deterministic():
    out1 = _run_ranker()
    out2 = _run_ranker()

    assert out1 == out2


def test_ranker_output_is_non_empty_for_enabled_games():
    out = _run_ranker()

    assert isinstance(out, list)
    assert out, "Ranker produced no output"


def test_ranker_handles_empty_candidates():
    ranker = DeterministicRanker()

    out = ranker.rank(
        candidate_game_ids=[],
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
        game_profiles={},
    )

    assert out == []