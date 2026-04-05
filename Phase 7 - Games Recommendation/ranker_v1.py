from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from .types import RecommendationContext, RecommendationItem


class DeterministicBaselineRankerV1:
    VERSION = "v1"

    def rank(
        self,
        *,
        candidate_game_ids: List[str],
        ctx: RecommendationContext,
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        version: str = "v1",
    ) -> List[RecommendationItem]:
        _ = (ctx, player_profile, player_history, version)

        items: List[RecommendationItem] = []
        for gid in candidate_game_ids:
            items.append(
                RecommendationItem(
                    game_id=str(gid),
                    score=_stable_score(str(gid)),
                    reasons=[],
                    constraints_applied=[],
                )
            )

        items.sort(key=lambda it: (-it.score, it.game_id))
        return items


def _stable_score(game_id: str) -> float:
    h = hashlib.sha256(game_id.encode("utf-8")).hexdigest()
    n = int(h[:12], 16)
    return (n % 1_000_000) / 1_000_000.0 + 1e-9
