"""
Scoring Availability (CI) — Wave 3

CI check: every eligible game must be scorable by the ranker.
This is NON-SEMANTIC:
- does not require a minimum score
- only requires that a score exists and is finite.

NOTE:
- Eligibility exclusions are CI-only governance.
- Runtime must not import eligibility policy.
"""

import math

from rhythm_recommendation.phase7.ranking import DeterministicRanker
from rhythm_recommendation.phase7.registry import GameInfo, GameRegistry
from rhythm_recommendation.phase7.eligibility import EXPLICIT_EXCLUSIONS


def test_scoring_availability_for_recommendable_games():
    # Minimal registry in CI (do not require real games.json)
    registry = GameRegistry(
        games=[
            GameInfo(game_id="proseka", status="enabled", display_name="Project SEKAI"),
            GameInfo(game_id="arcaea", status="enabled", display_name="Arcaea"),
            GameInfo(game_id="chunithm", status="enabled", display_name="CHUNITHM"),
            GameInfo(game_id="ongeki", status="enabled", display_name="ONGEKI"),
        ]
    )

    candidate_ids = registry.recommendable_game_ids(strict=True)
    assert candidate_ids, "Expected at least one recommendable game"

    ranker = DeterministicRanker()
    items = ranker.rank(
        candidate_game_ids=candidate_ids,
        ctx={"player_id": "p1", "locale": "en"},
        player_profile={},
        player_history={},
        game_profiles=None,
    )

    scored = {it.game_id: it.score for it in items}

    for gid in candidate_ids:
        if gid in EXPLICIT_EXCLUSIONS:
            continue

        assert gid in scored, f"{gid} missing from ranker output"
        s = float(scored[gid])

        assert not math.isnan(s), f"{gid} score is NaN"
        assert math.isfinite(s), f"{gid} score is not finite"