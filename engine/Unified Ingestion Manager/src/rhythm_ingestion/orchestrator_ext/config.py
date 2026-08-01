"""
rhythm_ingestion.orchestrator_ext.config

Configuration schema for orchestrator extensions.
Additive; must not replace games.json.

Design:
- Instantiable with no args (bridge default)
- Read-only semantics; no gameplay logic
- Wiring-flexible: per-game defaults are advisory, not authoritative
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .feature_flags import FeatureFlags


@dataclass(frozen=True)
class PerGameDefaults:
    lane_offset: Optional[int] = None
    ticks_per_beat: Optional[int] = None
    time_unit: Optional[str] = None
    ingestion_only: Optional[bool] = None


@dataclass(frozen=True)
class RetryPolicy:
    enabled: bool = False
    max_attempts: int = 2


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    enabled: bool = False
    open_after: int = 3


@dataclass(frozen=True)
class OrchestratorExtensionConfig:
    """
    Top-level extension configuration.

    feature_flags:
      - controls whether orchestrator_ext wraps the core at all
      - all False => thin pass-through behavior

    strict_preflight:
      - if True, preflight failures should hard-fail the run
      - if False, preflight failures may degrade safely (stabilizer-owned)
    """

    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    breaker_policy: CircuitBreakerPolicy = field(default_factory=CircuitBreakerPolicy)
    per_game: Dict[str, PerGameDefaults] = field(default_factory=dict)
    strict_preflight: bool = False

    def per_game_defaults(self, game_id: str) -> PerGameDefaults:
        """
        Read-only helper: returns per-game defaults if present, else empty defaults.
        """
        g = str(game_id or "").strip()
        v = self.per_game.get(g)
        return v if isinstance(v, PerGameDefaults) else PerGameDefaults()

    def any_feature_enabled(self) -> bool:
        """Convenience wrapper for bridge / stabilizer gating."""
        return bool(self.feature_flags.any_enabled())


__all__ = [
    "PerGameDefaults",
    "RetryPolicy",
    "CircuitBreakerPolicy",
    "OrchestratorExtensionConfig",
]