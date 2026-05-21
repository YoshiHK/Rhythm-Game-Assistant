from registry.registry import load_games_registry
from eligibility.eligibility_policy import EXPLICIT_EXCLUSIONS


def is_data_ready(game) -> bool:
    # ✅ minimal CI definition
    return bool(getattr(game, "display_name", None))


def test_recommendation_data_readiness():
    registry = load_games_registry("games.json")

    for game in registry.games:
        if getattr(game, "overall_status", None) not in ("enabled", "anchor"):
            continue

        if game.game_id in EXPLICIT_EXCLUSIONS:
            continue

        assert is_data_ready(game), f"{game.game_id} is not data-ready"
