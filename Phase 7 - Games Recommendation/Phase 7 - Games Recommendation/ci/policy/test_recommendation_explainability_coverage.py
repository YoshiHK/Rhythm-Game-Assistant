"""
Explainability Coverage (CI) — Phase 7 (registry-driven)

Non-semantic:
- does NOT evaluate explanation quality
- only ensures presence of explanation surface

Source of truth:
- games.json
"""

from ranking.ranker import DeterministicRanker
from explanation.explanation_engine import ExplanationEngine
from registry import load_games_registry


def _rank_items():
    registry = load_games_registry("games.json")

    # ✅ only include recommendable games
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
        game_profiles={},  # non-semantic placeholder
    )

    explainer = ExplanationEngine()

    return explainer.attach_explanations(items)


def test_explainability_contract_coverage():
    items1 = _rank_items()
    items2 = _rank_items()

    # ✅ deterministic
    assert items1 == items2

    assert items1, "No recommendation items produced"

    for item in items1:
        # ✅ allow both dict / object depending on impl
        explanation = getattr(item, "explanation", None)
        if explanation is None and isinstance(item, dict):
            explanation = item.get("explanation")

        assert explanation is not None, "Missing explanation field"