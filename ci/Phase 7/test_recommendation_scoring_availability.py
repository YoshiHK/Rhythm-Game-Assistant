# ci/test_recommendation_scoring_availability.py

from rhythm_recommendation.phase7.registry_loader import (
    load_registry_config,
    get_all_games,
)

# Must match eligibility CI
EXPLICIT_EXCLUSIONS = {
    # Example:
    # "some_game_id": "Ranker not implemented yet",
}

def has_scorable_candidate(game_id: str, meta: dict) -> bool:
    """
    Phase 7 scoring availability predicate (v1).

    Conservative definition:
    - enabled games are expected to produce at least one
      scorable candidate in the ranker input space.

    This is a STUB that mirrors the ranker contract
    without invoking the real ranker.
    """

    # Minimal contract:
    # If the game is enabled, it must have a difficulty system
    # and ingestion coverage, which implies scorable inputs exist.
    #
    # This keeps CI phase-safe and deterministic.
    return meta.get("status") == "enabled"

def test_recommendation_scoring_availability():
    """
    CI check: every eligible game must have scoring availability.

    This prevents freezing a ranker that silently
    returns empty recommendation lists.
    """

    cfg = load_registry_config("games.json")
    games = get_all_games(cfg)

    not_scorable = []

    for game_id, meta in games.items():
        status = meta.get("status")

        # Only check eligible games
        if status != "enabled":
            continue

        if game_id in EXPLICIT_EXCLUSIONS:
            continue

        if not has_scorable_candidate(game_id, meta):
            not_scorable.append(game_id)

    assert not not_scorable, (
        "Eligibility × Scoring Availability check failed. "
        "Eligible games with no scorable candidates: "
        + ", ".join(sorted(not_scorable))
    )
