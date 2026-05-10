# test_ranker_regression.py

import pytest

from rhythm_recommendation.phase7.ranking import DeterministicRanker
from rhythm_recommendation.phase7.contracts.types import RecommendationItem


def _run_scenario():
    ranker = DeterministicRanker()
    return ranker.rank(
        candidate_game_ids=["proseka", "arcaea", "chunithm", "ongeki"],
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new"},
        player_history={"recent_games": []},
    )


def test_ranker_regression_order_is_stable():
    """
    Regression guard:
    the relative ordering must not change for the same inputs.
    """
    out1 = _run_scenario()
    out2 = _run_scenario()

    ids1 = [it.game_id for it in out1]
    ids2 = [it.game_id for it in out2]

    assert ids1 == ids2


def test_ranker_scores_are_stable():
    """
    Regression guard:
    scores must be numerically identical for same inputs.
    """
    out1 = _run_scenario()
    out2 = _run_scenario()

    scores1 = [it.score for it in out1]
    scores2 = [it.score for it in out2]

    assert scores1 == scores2


def test_ranker_outputs_contract_items():
    """
    Regression guard:
    ranker must emit contract-shaped items.
    """
    out = _run_scenario()
    assert out

    for it in out:
        assert isinstance(it, RecommendationItem)
        assert isinstance(it.game_id, str)
        assert isinstance(it.score, float)
        assert isinstance(it.rationale, dict)