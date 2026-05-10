from __future__ import annotations
from dataclasses import Any, Dict, List, Optionalfrom dataclasses import dataclass


class RunMode(str, Enum):
    FULL = 'full'
    RANK_ONLY = 'rank_only'
    EXPLAIN_ONLY = 'explain_only'


@dataclass(frozen=True)
class RecommendationContext:
    player_id: str
    locale: str = 'en'
    top_k: int = 3
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class RecommendationItem:
    game_id: str
    score: float
    reasons: List[Dict[str, Any]]
    constraints_applied: List[str]


@dataclass
class RecommendationResult:
    """
    Phase 7 recommendation result.

    Note:
    - No ranker version is exposed.
    - Ranking behavior is single-source and authoritative.
    """
    player_id: str
    locale: str
    generated_at_iso: str
    items: List[RecommendationItem]
    diagnostics: Dict[str, Any]
from enum import Enum
