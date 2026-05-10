"""
Phase 7 — Games Recommendations
Contracts Layer

This package exposes the stable public contracts for Phase 7.

Notes:
- Phase 7 exposes a single authoritative recommendation contract.
- No runtime versioning is supported.
- Consumers should not depend on implementation details.
"""

from .types import (
    RecommendationContext,
    RecommendationItem,
    RecommendationResult,
    RunMode,
)
from .config import Phase7Config
from .feature_flags import FeatureFlags

__all__ = [
    "RecommendationContext",
    "RecommendationItem",
    "RecommendationResult",
    "RunMode",
    "Phase7Config",
    "FeatureFlags",
]