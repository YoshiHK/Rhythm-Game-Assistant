# test_recommendation_data_readiness.py
#
# Phase 7 CI — Data Readiness (Wave 2)
#
# Purpose:
# - Ensure that games which are eligible for recommendation
#   have the minimum presentation-safe data required.
#
# Non-goals:
# - This test does NOT decide eligibility.
# - This test does NOT perform ranking.
# - This test does NOT import Phase 6 or runtime logic.

from registry.registry import GameInfo, GameRegistry
from eligibility.eligibility_policy import EXPLICIT_EXCLUSIONS


def is_data_ready(game: GameInfo) -> bool:
    """
    Phase 7 data readiness predicate (Wave 2).

    Minimal, conservative definition:
    - display_name must exist and be non-empty

    NOTE:
    - This is intentionally weaker than eligibility.
    - Eligibility exclusions are handled elsewhere.
    """
    return bool(game.display_name and str(game.display_name).strip())


def test_recommendation_data_readiness():
    """
    CI guarantee:
    Every recommendable game must be data-ready,
    unless it is explicitly excluded by eligibility policy.
    """
    registry = GameRegistry(
        games=[
            GameInfo(
                game_id="proseka",
                status="enabled",
                display_name="Project SEKAI",
            ),
            GameInfo(
                game_id="arcaea",
                status="enabled",
                display_name="Arcaea",
            ),
            GameInfo(
                game_id="chunithm",
                status="enabled",
                display_name=None,  # Missing UI-safe data
            ),
        ]
    )

    recommendable = registry.recommendable_game_ids(strict=True)

    for game_id in recommendable:
        # Eligibility exclusions override data readiness
        if game_id in EXPLICIT_EXCLUSIONS:
            continue

        game = registry.get(game_id)
        assert game is not None, f"Game {game_id} missing from registry"

        assert is_data_ready(
            game
        ), f"Game '{game_id}' is recommendable but not data-ready"