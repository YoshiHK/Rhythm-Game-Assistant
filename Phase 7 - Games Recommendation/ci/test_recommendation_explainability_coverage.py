"""
Explainability Coverage (CI) — Wave 3

Phase 7 requires recommendations to be explainable.
This test is NON-SEMANTIC:
- does not judge explanation quality
- only validates that the explainability contract surface exists

What it enforces:
- ranker outputs are deterministic for identical inputs
- explanation engine attaches bounded explanation fields to every item
"""

from rhythm_recommendation.phase7.ranking import DeterministicRanker
from rhythm_recommendation.phase7.explanation import ExplanationEngine
from rhythm_recommendation.phase7.contracts.types import RecommendationItem


def _rank_items():
    ranker = DeterministicRanker()
    return ranker.rank(
        candidate_game_ids=["proseka", "arcaea", "chunithm", "ongeki"],
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={"experience_level": "new", "tags": ["practice"]},
        player_history={"recent_games": []},
        game_profiles={
            "proseka": {"tags": ["practice", "balanced"], "complexity": 0.4},
            "arcaea": {"tags": ["challenge"], "complexity": 0.8},
            "chunithm": {"tags": ["stamina", "challenge"], "complexity": 0.7},
            "ongeki": {"tags": ["variety", "balanced"], "complexity": 0.5},
        },
    )


def test_explainability_contract_coverage():
    items1 = _rank_items()
    items2 = _rank_items()

    # Deterministic output for identical inputs (order + values)
    assert items1 == items2

    # Explanation layer must attach explanation surface to every item
    engine = ExplanationEngine(max_why=4)
    out = engine.explain_items(items=items1, ctx={"locale": "en"})

    assert isinstance(out, list)
    assert out, "Expected at least one recommendation item"

    for it in out:
        assert isinstance(it, RecommendationItem)
        assert isinstance(it.rationale, dict)

        explanation = it.rationale.get("explanation")
        assert isinstance(explanation, dict), "Missing rationale['explanation']"
        assert isinstance(explanation.get("summary"), str), "Missing explanation summary"
        why = explanation.get("why")
        assert isinstance(why, list), "Missing explanation why list"

        # Bounded explainability (max_why)
        assert len(why) <= 4
        for entry in why:
            assert isinstance(entry, dict)
            assert isinstance(entry.get("code"), str)
            assert isinstance(entry.get("message"), str)