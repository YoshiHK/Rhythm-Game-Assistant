# test_ranker.py

from rhythm_recommendation.phase7.ranking import DeterministicRanker
from rhythm_recommendation.phase7.contracts.types import RecommendationItem


def _run_ranker():
    ranker = DeterministicRanker()
    return ranker.rank(
        candidate_game_ids=["game_a", "game_b", "game_c"],
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={},
        player_history={},
    )


def test_ranker_is_deterministic():
    """
    Same inputs must produce identical outputs.
    """
    out1 = _run_ranker()
    out2 = _run_ranker()

    assert out1 == out2


def test_ranker_output_shape():
    """
    Ranker must return contract-shaped RecommendationItem objects.
    """
    out = _run_ranker()
    assert len(out) > 0

    for it in out:
        assert isinstance(it, RecommendationItem)
        assert isinstance(it.game_id, str)
        assert isinstance(it.score, float)
        assert isinstance(it.rationale, dict)


def test_ranker_handles_empty_candidates():
    """
    Ranker must handle empty candidate list safely.
    """
    ranker = DeterministicRanker()
    out = ranker.rank(
        candidate_game_ids=[],
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={},
        player_history={},
    )
    assert out == []