from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional

from contracts.types import RecommendationItem


def _stable_score(token: Any) -> float:
    """Stable baseline score in [0,1)."""
    h = hashlib.sha256(str(token).encode("utf-8")).hexdigest()
    n = int(h[:12], 16)
    return (n % 1_000_000) / 1_000_000.0


def _make_item(game_id: str, score: float) -> Any:
    """
    Try to construct a RecommendationItem in a contract-compatible way.
    Falls back to dict if the contract shape differs.
    """
    # Try dataclass fields first (most robust)
    fields = getattr(RecommendationItem, "__dataclass_fields__", None)
    if fields:
        kwargs: Dict[str, Any] = {}
        if "game_id" in fields:
            kwargs["game_id"] = game_id
        elif "id" in fields:
            kwargs["id"] = game_id

        if "score" in fields:
            kwargs["score"] = float(score)
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

    # Try common constructor signatures
    for kwargs in (
        {"game_id": game_id, "score": float(score)},
        {"id": game_id, "score": float(score)},
    ):
        try:
            return RecommendationItem(**kwargs)  # type: ignore
        except Exception:
            continue

    # Fallback dict (tests in this repo were made tolerant)
    return {"game_id": game_id, "score": float(score)}


class DeterministicRanker:
    """
    Deterministic games recommendation ranker (CI baseline).

    Non-goals:
    - no learning
    - no I/O
    - no free-form generation
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

            # Small deterministic penalties/bonuses (still non-semantic)
            if gid in recent:
                base = base - 0.10
            else:
                base = base + 0.05

            score = max(0.0, min(1.0, base))
            if not math.isfinite(score):
                score = 0.0

            out.append(_make_item(gid, score))

        # Sort deterministically: score desc, game_id asc
        def key_fn(x: Any):
            if isinstance(x, dict):
                gid = x.get("game_id") or x.get("id") or ""
                sc = x.get("score", 0.0)
            else:
                gid = getattr(x, "game_id", None) or getattr(x, "id", "") or ""
                sc = getattr(x, "score", 0.0)
            return (-float(sc), str(gid))

        out.sort(key=key_fn)
        return out


__all__ = ["DeterministicRanker"]