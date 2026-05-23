from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class GameInfo:
    """
    Phase 7 Game Metadata

    Compatibility:
    - Supports BOTH:
        ✅ overall_status (new, from games.json)
        ✅ status (legacy tests / code)
    """

    game_id: str
    display_name: str
    overall_status: Optional[str] = None

    def __init__(
        self,
        *,
        game_id: str,
        display_name: str,
        overall_status: Optional[str] = None,
        status: Optional[str] = None,
    ):
        resolved_status = overall_status if overall_status is not None else status

        if resolved_status is None:
            raise ValueError("GameInfo requires either overall_status or status")

        object.__setattr__(self, "game_id", str(game_id))
        object.__setattr__(self, "display_name", str(display_name))
        object.__setattr__(self, "overall_status", str(resolved_status))

    # ✅ backward compatible alias
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