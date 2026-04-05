
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


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
    player_id: str
    locale: str
    generated_at_iso: str
    ranker_version: str
    items: List[RecommendationItem]
    diagnostics: Dict[str, Any]
