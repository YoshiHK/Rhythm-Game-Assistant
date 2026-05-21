from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GameInfo:
    """
    Canonical game metadata for Phase 7 registry filtering.
    """

    game_id: str
    display_name: str
    status: str


class GameRegistry:
    """
    Read-only registry for Phase 7 game eligibility.

    Design:
    - Immutable container
    - CI-safe
    - No side effects
    """

    def __init__(self, games: List[GameInfo]):
        self._games = list(games)

    @property
    def games(self) -> List[GameInfo]:
        return list(self._games)