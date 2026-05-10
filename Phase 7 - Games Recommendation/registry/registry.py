from __future__ import annotations

from dataclasses import Optionalfrom dataclasses import dataclass


@dataclass(frozen=True)
class GameInfo:
    """
    Canonical game metadata for Phase 7 registry filtering.

    This structure is intentionally minimal.
    """
    game_id: str
    status: str
    display_name: Optional[str] = None


class GameRegistry:
    """
    Read-only registry for Phase 7 game eligibility.

    The registry does not reinterpret status values.
    It only filters based on explicit, documented rules.
    """

    def __init__(self, entries: Iterable[GameInfo]):
        self._entries: Dict[str, GameInfo] = {
            info.game_id: info for info in entries
        }

    def all_games(self) -> List[GameInfo]:
        """
        Return all registered games, in stable order.
        """
        return [self._entries[k] for k in sorted(self._entries)]

    def recommendable_game_ids(self, *, strict: bool = True) -> List[str]:
        """
        Return game_ids eligible for Phase 7 recommendations.

        strict=True:
            - only games with status == 'enabled'

        strict=False:
            - games with status in {'enabled', 'ingestion_only'}
        """
        allowed = {"enabled"} if strict else {"enabled", "ingestion_only"}
        return sorted(
            gid
            for gid, info in self._entries.items()
            if str(info.status) in allowed
        )

    def get(self, game_id: str) -> Optional[GameInfo]:
        """
        Retrieve a single GameInfo entry.
        """
        return self._entries.get(game_id)
