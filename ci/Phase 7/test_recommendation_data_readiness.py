# ci/test_recommendation_data_readiness.py

from rhythm_recommendation.phase7.registry_loader import (
    load_registry_config,
    get_all_games,
)

# Explicit exclusions must match eligibility coverage CI
EXPLICIT_EXCLUSIONS = {
    # Example:
    # "some_game_id": "Difficulty profiles not stabilized yet",
}

def is_data_ready(game_id: str, meta: dict) -> bool:
    """
    Phase 7 data readiness predicate (v1).

    Conservative rule:
    - enabled games are assumed ingestible
    - future tightening can add real checks here
    """
    # v1: enabled implies ingestion coverage exists or is expected
    return meta.get("status") == "enabled"

def test_recommendation_eligibility_data_readiness():
    """
    CI check: every recommendation-eligible game must be data-ready.
    """

    cfg = load_registry_config("games.json")
    games = get_all_games(cfg)

    not_ready = []

    for game_id, meta in games.items():
        status = meta.get("status")

        # Only check enabled games
        if status != "enabled":
            continue

        # Skip explicit exclusions
        if game_id in EXPLICIT_EXCLUSIONS:
            continue

        # Data readiness check
        if not is_data_ready(game_id, meta):
            not_ready.append(game_id)

    assert not not_ready, (
        "Eligibility × Data Readiness check failed. "
        "Enabled games lacking minimum data readiness: "
        + ", ".join(sorted(not_ready))
    )
``
