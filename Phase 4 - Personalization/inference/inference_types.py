from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PlayerContext:
    player_id_hash: Optional[str] = None
    locale: Optional[str] = None
    cohort: Optional[str] = None


@dataclass(frozen=True)
class InferenceInputs:
    engine_mode: str
    difficulty: str
    elements_skeleton: List[Dict[str, Any]]
    canonical_payload: Dict[str, Any]
    canonical_row: Dict[str, Any]
    player: PlayerContext


@dataclass(frozen=True)
class InferenceOutputs:
    ranking_weights: Dict[str, float]
    element_ordering: Optional[List[str]]
    narrative_template_id: Optional[str]
    variant_id: Optional[str]
    bandit_meta: Optional[Dict[str, Any]]