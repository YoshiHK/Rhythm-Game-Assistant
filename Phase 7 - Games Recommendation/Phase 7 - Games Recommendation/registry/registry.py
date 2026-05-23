from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GameInfo:
    """
    Canonical game metadata for Phase 7.

    Field source:
    - games.json uses `overall_status`
    Compatibility:
    - expose `.status` as an alias to `.overall_status`
    """
    game_id: str
    display_name: str
    overall_status: str

    @property
    def status(self) -> str:
        return self.overall_status


class GameRegistry:
    """
    Read-only registry for Phase 7 game eligibility.
    """

    def __init__(self, games: List[GameInfo]):
        self._games = list(games)

    @property
    def games(self) -> List[GameInfo]:
        return list(self._games)