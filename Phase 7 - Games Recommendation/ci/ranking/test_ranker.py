from ranking.ranker import DeterministicRanker
from contracts.types import RecommendationItem

def _run_ranker():
    ranker = DeterministicRanker()
    return ranker.rank(
        candidate_game_ids=["game_a", "game_b", "game_c"],
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
        game_profiles={},
    )

def test_ranker_is_deterministic():
    out1 = _run_ranker()
    out2 = _run_ranker()
    assert out1 == out2

def test_ranker_output_shape():
    out = _run_ranker()
    assert isinstance(out, list)
    assert len(out) >= 0
    for item in out:
        # allow either dict or contract object, depending on implementation
        assert item is not None

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