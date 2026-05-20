# ci/test_recommendation_score_diversity.py

"""Eligibility × Score Diversity (CI)

Quality floor check for Phase 7:
- For eligible games, ranking should not be degenerate (e.g., all scores identical).

Update: Per-player profile scenarios
-----------------------------------
This test now validates score diversity under multiple *player profile* scenarios.
The ranker may use or ignore these profiles depending on implementation, but the
diversity requirement applies in all cases.

Constraints:
- Phase 7 only: uses Phase 7 router + injected/default ranker.
- Deterministic and CI-safe: does not call completed phase runtime.
"""

from contracts.feature_flags import FeatureFlags
from contracts.config import Phase7Config
from registry.registry_loader import load_registry_config, get_all_games
from contracts.types import RecommendationContext, RunMode


# Must match eligibility CI policy registry (keep empty unless you intentionally exclude)
EXPLICIT_EXCLUSIONS = {
    # "some_game_id": "Excluded from recommendations until ready",
}


def _eligible_registry_dict() -> tuple[dict, list[str]]:
    cfg = load_registry_config("games.json")
    games = get_all_games(cfg)

    reg_dict: dict = {}
    eligible: list[str] = []
    for gid, meta in games.items():
        if meta.get("status") != "enabled":
            continue
        if gid in EXPLICIT_EXCLUSIONS:
            continue
        eligible.append(gid)
        reg_dict[gid] = {
            "status": meta.get("status"),
            "display_name": meta.get("display_name"),
        }
    return reg_dict, eligible


def test_recommendation_score_diversity_per_player_scenario():
    reg_dict, eligible = _eligible_registry_dict()

    # If only one eligible game exists, diversity is not meaningful.
    if len(eligible) <= 1:
        return

    router = build_phase7_router(
        config=Phase7Config(
            feature_flags=FeatureFlags(enable_phase7=True),
            ranker_version="v1",
        ),
        registry=build_registry_from_dict(reg_dict),
    )

    # Per-player profile scenarios (schema-free dicts; ranker may choose to use them)
    scenarios = [
        (
            "new_player",
            {"experience_level": "new", "avg_clear_rate": 0.60, "preferred_session_minutes": 10},
            {"history_version": "v1", "recent_games": []},
        ),
        (
            "intermediate_player",
            {"experience_level": "intermediate", "avg_clear_rate": 0.85, "pattern_affinity": ["holds", "trills"]},
            {"history_version": "v1", "recent_games": ["proseka"]},
        ),
        (
            "advanced_player",
            {"experience_level": "advanced", "avg_clear_rate": 0.97, "stamina_proxy": 0.9, "timing_strictness": "high"},
            {"history_version": "v1", "recent_games": ["chunithm", "arcaea"]},
        ),
    ]

    top_k = min(5, len(eligible))

    for scenario_name, player_profile, player_history in scenarios:
        ctx = RecommendationContext(player_id=f"ci_probe::{scenario_name}", locale="en", top_k=top_k)

        # Run twice to ensure determinism for the same scenario inputs.
        res1 = router.recommend_games(
            ctx=ctx,
            mode=RunMode.RANK_ONLY,
            player_profile=player_profile,
            player_history=player_history,
        )
        res2 = router.recommend_games(
            ctx=ctx,
            mode=RunMode.RANK_ONLY,
            player_profile=player_profile,
            player_history=player_history,
        )

        assert len(res1.items) == top_k, (
            f"[{scenario_name}] Expected {top_k} items, got {len(res1.items)}"
        )

        sig1 = [(it.game_id, float(it.score)) for it in res1.items]
        sig2 = [(it.game_id, float(it.score)) for it in res2.items]
        assert sig1 == sig2, f"[{scenario_name}] Non-deterministic output: {sig1} != {sig2}"

        scores = [float(it.score) for it in res1.items]
        unique_scores = len(set(scores))

        # Diversity rule: at least 2 unique scores when top_k >= 2
        if top_k >= 2:
            assert unique_scores >= 2, (
                f"[{scenario_name}] Eligibility × Score Diversity failed: "
                f"top_k={top_k} returned only {unique_scores} unique score(s): {scores}"
            )
