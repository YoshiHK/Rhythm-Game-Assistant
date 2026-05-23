"""
Phase 7 — Contracts package (flat exports)

Design:
- Versionless contract surface
- No runtime logic
- Safe for CI import
"""

from contracts.types import (
    RecommendationItem,
    RunMode,
)

from contracts.config import Phase7Config
from contracts.feature_flags import FeatureFlags

__all__ = [
    "RecommendationItem",
    "RunMode",
    "Phase7Config",
    "FeatureFlags",
]