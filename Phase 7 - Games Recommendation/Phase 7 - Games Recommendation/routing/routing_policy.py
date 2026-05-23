from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


class _RegistryLike(Protocol):
    """
    Minimal registry protocol required by routing.

    Routing only relies on stable, read-only registry calls.
    Optional filters are invoked only when present and must be non-blocking.
    """

    def recommendable_game_ids(self, *, strict: bool = True) -> List[str]:
        ...

    # Optional (if provided by registry implementation)
    def filter_by_platform(self, game_ids: List[str], *, platform: Optional[str]) -> List[str]:
        ...

    def filter_by_locale(self, game_ids: List[str], *, locale: Optional[str]) -> List[str]:
        ...


@dataclass(frozen=True)
class Phase7RoutingPolicy:
    """
    Declarative routing policy for Phase 7.

    NOTE:
    - This policy does NOT implement learning or ranking.
    - It only defines routing-safe candidate shaping.
    - It must remain non-blocking: errors in filters must not crash routing.

    strict_registry:
        True  -> only registry status == 'enabled'
        False -> allow {'enabled', 'ingestion_only'} (internal/testing)
    """

    strict_registry: bool = True

    def select_candidates(
        self,
        *,
        registry: _RegistryLike,
        platform: Optional[str],
        locale: Optional[str],
    ) -> List[str]:
        # Base candidate set from registry
        candidates = registry.recommendable_game_ids(strict=self.strict_registry)

        # Apply platform filter if supported (non-blocking)
        if platform and hasattr(registry, "filter_by_platform"):
            try:
                candidates = registry.filter_by_platform(candidates, platform=platform)  # type: ignore[attr-defined]
            except Exception:
                pass

        # Apply locale filter if supported (non-blocking)
        if locale and hasattr(registry, "filter_by_locale"):
            try:
                candidates = registry.filter_by_locale(candidates, locale=locale)  # type: ignore[attr-defined]
            except Exception:
                pass

        return list(candidates)