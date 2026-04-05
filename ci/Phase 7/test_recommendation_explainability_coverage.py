"""Eligibility × Explainability Coverage (CI)

Phase 7 requires recommendations to be explainable.

In v1, explanation generation may be deferred, but the *contract surface* must exist
so downstream systems can attach and render rationales.

This test validates:
- deterministic output for identical inputs
- every RecommendationItem includes explainability fields (`reasons`, `constraints_applied`)

NOTE: This test is intentionally non-semantic. It does NOT judge explanation quality.
"""

from __future__ import annotations

from rhythm_recommendation.phase7.feature_flags import FeatureFlags
from rhythm_recommendation.phase7.config import Phase7Config
from rhythm_recommendation.phase7.registry_loader import load_registry_config, get_all_games
from rhythm_recommendation.phase7.build import build_phase7_router, build_registry_from_dict
from rhythm_recommendation.phase7.types import RecommendationContext, RunMode


# Must match eligibility CI policy registry (keep empty unless you intentionally exclude)
EXPLICIT_EXCLUSIONS = {
    # "some_game_id": "Excluded from recommendations until ready",
}


def test_recommendation_explainability_contract_coverage():
    cfg = load_registry_config("games.json")
    games = get_all_games(cfg)

    reg_dict = {}
    eligible = []
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

    if not eligible:
        return

    router = build_phase7_router(
        config=Phase7Config(feature_flags=FeatureFlags(enable_phase7=True), ranker_version="v1"),
        registry=build_registry_from_dict(reg_dict),
    )

    top_k = min(5, len(eligible))
    ctx = RecommendationContext(player_id="ci_probe::explainability", locale="en", top_k=top_k)

    player_profile = {"experience_level": "new"}
    player_history = {"history_version": "v1", "recent_games": []}

    res1 = router.recommend_games(ctx=ctx, mode=RunMode.RANK_ONLY, player_profile=player_profile, player_history=player_history)
    res2 = router.recommend_games(ctx=ctx, mode=RunMode.RANK_ONLY, player_profile=player_profile, player_history=player_history)

    sig1 = [(it.game_id, float(it.score)) for it in res1.items]
    sig2 = [(it.game_id, float(it.score)) for it in res2.items]
    assert sig1 == sig2, f"Non-deterministic output: {sig1} != {sig2}"

    assert len(res1.items) == top_k, f"Expected {top_k} items, got {len(res1.items)}"

    for it in res1.items:
        assert isinstance(it.game_id, str) and it.game_id
        _ = float(it.score)

        assert hasattr(it, "reasons"), "RecommendationItem missing reasons field"
        assert isinstance(it.reasons, list), f"reasons must be a list, got {type(it.reasons)}"

        assert hasattr(it, "constraints_applied"), "RecommendationItem missing constraints_applied field"
        assert isinstance(it.constraints_applied, list), f"constraints_applied must be a list, got {type(it.constraints_applied)}"
