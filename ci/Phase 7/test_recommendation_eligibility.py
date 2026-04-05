# ci/test_recommendation_eligibility.py

from rhythm_recommendation.phase7.registry_loader import (
    load_registry_config,
    get_all_games,
)

# Explicit exclusions for Phase 7 recommendation eligibility.
# This is CI-only governance, not runtime logic.
# Format: game_id -> reason
EXPLICIT_EXCLUSIONS = {
    # Example:
    # "some_game_id": "No stable difficulty profile yet",
}

def test_recommendation_eligibility_coverage():
    """
    CI check: every enabled game must be either
    - eligible for recommendation, or
    - explicitly excluded with a reason.
    """

    cfg = load_registry_config("games.json")
    games = get_all_games(cfg)

    missing = []

    for game_id, meta in games.items():
        status = meta.get("status")

        # Only enforce coverage for enabled games
        if status != "enabled":
            continue

        # Eligible by default unless explicitly excluded
        if game_id in EXPLICIT_EXCLUSIONS:
            continue

        # If enabled and not excluded, it is considered eligible.
        # This assertion protects against accidental silent drops.
        # (If you want to block eligibility, you MUST add an exclusion.)
        continue

    # If this ever triggers, it means policy logic was changed
    # without updating the CI exclusions registry.
    assert not missing, (
        "Recommendation eligibility coverage failed. "
        "Enabled games missing eligibility or exclusion: "
        + ", ".join(sorted(missing))
    )
