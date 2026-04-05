
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import Phase7Config
from .registry import GameRegistry
from .types import RecommendationContext, RecommendationItem, RecommendationResult, RunMode


class Phase7Router:
    """Phase 7 routing-only entrypoint.

    Orchestrates registry filtering and ranker invocation.
    """

    def __init__(self, *, config: Phase7Config, registry: GameRegistry, ranker: Optional[Any] = None, explainer: Optional[Any] = None):
        self.config = config
        self.registry = registry
        self.ranker = ranker
        self.explainer = explainer

    def recommend_games(self, *, ctx: RecommendationContext, mode: RunMode = RunMode.FULL, player_profile: Optional[Dict[str, Any]] = None, player_history: Optional[Dict[str, Any]] = None) -> RecommendationResult:
        if not self.config.feature_flags.enable_phase7:
            return self._empty(ctx, 'phase7_disabled')

        candidates = self.registry.recommendable_game_ids(strict=True)
        if not candidates:
            return self._empty(ctx, 'no_candidates')

        ranked: List[RecommendationItem] = []
        if mode in (RunMode.FULL, RunMode.RANK_ONLY) and self.ranker:
            ranked = self.ranker.rank(candidate_game_ids=candidates, ctx=ctx, player_profile=player_profile or {}, player_history=player_history or {}, version=str(self.config.ranker_version))

        ranked = ranked[: int(ctx.top_k)]

        return RecommendationResult(
            player_id=ctx.player_id,
            locale=ctx.locale,
            generated_at_iso=datetime.now(timezone.utc).isoformat(),
            ranker_version=str(self.config.ranker_version),
            items=ranked,
            diagnostics={'mode': mode.value},
        )

    def _empty(self, ctx: RecommendationContext, reason: str) -> RecommendationResult:
        return RecommendationResult(
            player_id=ctx.player_id,
            locale=ctx.locale,
            generated_at_iso=datetime.now(timezone.utc).isoformat(),
            ranker_version=str(self.config.ranker_version),
            items=[],
            diagnostics={'empty_reason': reason},
        )
