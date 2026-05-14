"""
Phase 6 — Song Recommendation Domain

This package implements runtime orchestration for song recommendations
(mode="songs") under Phase 6 governance.

Contract (Non-Negotiable):
- Runtime behavior is deterministic and non-semantic.
- No learning or adaptation occurs at runtime.
- Selection logic MUST NOT depend on feedback outcomes.
- All learning is offline (Phase 5) and introduced via deployment only.

Responsibilities:
- Coordinate song recommendation flow
- Invoke catalog loading and deterministic selection
- Shape API-safe responses
- Emit forward-only feedback and observability signals

Non-Responsibilities:
- Gameplay analysis or tips generation
- Ranking or learning logic
- Runtime experimentation or model updates
"""

from .song_rec_coordinator import SongRecommendationCoordinator
from .request_normalizer import NormalizedSongRecRequest
from .response_shaper import shape_song_recommendation_response

__all__ = [
    "SongRecommendationCoordinator",
    "NormalizedSongRecRequest",
    "shape_song_recommendation_response",
]