"""rhythm_ingestion.orchestrator_ext.config

Configuration schema for orchestrator extensions.

Additive; must not replace games.json.
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
    feature_flags: FeatureFlags = FeatureFlags()
    retry_policy: RetryPolicy = RetryPolicy()
    breaker_policy: CircuitBreakerPolicy = CircuitBreakerPolicy()
    per_game: Dict[str, PerGameDefaults] = field(default_factory=dict)
    strict_preflight: bool = False
