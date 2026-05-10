# test_recommendation_eligibility.py

from rhythm_recommendation.phase7.registry import GameInfo, GameRegistry
from rhythm_recommendation.phase7.eligibility import EXPLICIT_EXCLUSIONS


def test_enabled_games_are_covered_by_eligibility_policy():
    """
    CI governance:
    every enabled game must be either
    - eligible for recommendation, or
    - explicitly excluded with a reason.
    """
    registry = GameRegistry(
        games=[
            GameInfo(game_id="proseka", status="enabled"),
            GameInfo(game_id="arcaea", status="enabled"),
            GameInfo(game_id="chunithm", status="enabled"),
        ]
    )

    enabled = registry.recommendable_game_ids(strict=True)

    for gid in enabled:
        assert (
            gid not in EXPLICIT_EXCLUSIONS
            or isinstance(EXPLICIT_EXCLUSIONS.get(gid), str)
        )