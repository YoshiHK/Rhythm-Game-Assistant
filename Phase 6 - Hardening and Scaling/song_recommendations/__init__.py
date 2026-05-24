"""
Phase 6 — Song Recommendations package

CI-safe export surface:
- Avoid importing coordinator at import-time (prevents pytest collection blow-ups)
- Expose small, stable primitives that are safe to import
"""

# Safe, low-level contracts (no side effects)
from .request_normalizer import (
    NormalizedSongRecRequest,
    RecentRecommendation,
    normalize_song_recommendation_request,
)

from .game_capability_resolver import (
    GameCapability,
    CapabilityError,
    resolve_game_capability,
    canonicalize_tier_id,
    canonicalize_completion_id,
)

from .persistence_policy import (
    PersistencePlan,
    compute_persistence_plan,
    build_rotation_deletions,
)

from .response_shaper import (
    shape_song_recommendation_response,
)

__all__ = [
    # request normalization
    "NormalizedSongRecRequest",
    "RecentRecommendation",
    "normalize_song_recommendation_request",
    # capabilities
    "GameCapability",
    "CapabilityError",
    "resolve_game_capability",
    "canonicalize_tier_id",
    "canonicalize_completion_id",
    # persistence
    "PersistencePlan",
    "compute_persistence_plan",
    "build_rotation_deletions",
    # response
    "shape_song_recommendation_response",
]