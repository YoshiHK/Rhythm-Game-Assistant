from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional

from contracts.types import RecommendationItem


def _stable_score(token: Any) -> float:
    """
    Stable baseline score in [0, 1).
    Deterministic across runs for same token.
    """
    h = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
    n = int(h[:12], 16)
    return (n % 1_000_000) / 1_000_000.0


def _item_game_id(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("game_id") or item.get("id") or "")
    return str(getattr(item, "game_id", None) or getattr(item, "id", "") or "")


def _item_score(item: Any) -> float:
    if isinstance(item, dict):
        s = item.get("score", 0.0)
        return float(s) if isinstance(s, (int, float)) else 0.0
    s = getattr(item, "score", 0.0)
    return float(s) if isinstance(s, (int, float)) else 0.0


def _make_item(game_id: str, score: float) -> Any:
    """
    Construct RecommendationItem when possible; fall back to dict otherwise.
    This keeps CI tolerant to contract evolution.
    """
    fields = getattr(RecommendationItem, "__dataclass_fields__", None)
    if fields:
        kwargs: Dict[str, Any] = {}
        if "game_id" in fields:
            kwargs["game_id"] = game_id
        elif "id" in fields:
            kwargs["id"] = game_id

        if "score" in fields:
            kwargs["score"] = float(score)

        # optional contract fields (safe defaults)
        if "rationale" in fields:
            kwargs["rationale"] = {}
        if "constraints" in fields:
            kwargs["constraints"] = []
        if "explanation" in fields:
            kwargs["explanation"] = None

        try:
            return RecommendationItem(**kwargs)
        except Exception:
            pass

    # common constructor shapes
    for kwargs in (
        {"game_id": game_id, "score": float(score)},
        {"id": game_id, "score": float(score)},
    ):
        try:
            return RecommendationItem(**kwargs)  # type: ignore
        except Exception:
            continue

    return {"game_id": game_id, "score": float(score)}


class DeterministicRanker:
    """
    Phase 7 deterministic ranker (CI baseline)

    Properties:
    - deterministic: same inputs => same outputs
    - no I/O
    - no runtime learning
    - bounded, auditable output
    """

    def rank(
        self,
        *,
        candidate_game_ids: List[str],
        ctx: Dict[str, Any],
        player_profile: Dict[str, Any],
        player_history: Dict[str, Any],
        game_profiles: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        if not candidate_game_ids:
            return []

        recent = set(player_history.get("recent_games") or [])
        out: List[Any] = []

        for gid in candidate_game_ids:
            base = _stable_score(gid)

            # deterministic, non-semantic nudges
            if gid in recent:
                base -= 0.10
            else:
                base += 0.05

            score = max(0.0, min(1.0, base))
            if not math.isfinite(score):
                score = 0.0

            out.append(_make_item(str(gid), score))

        # deterministic ordering
        out.sort(key=lambda x: (-_item_score(x), _item_game_id(x)))
        return out


__all__ = ["DeterministicRanker"]