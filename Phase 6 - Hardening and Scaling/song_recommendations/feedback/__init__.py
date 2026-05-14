"""
Phase 6 — Song Recommendation Feedback Layer

This package defines forward-only feedback emission for
Song Recommendations.

Contract (Non-Negotiable):
- Observational only
- No runtime learning or adaptation
- No influence on song selection or ranking
- All learning occurs offline (Phase 5) via deployment

This layer exists to make Song Recommendations
safe to learn from, without making them unsafe to run.
"""

from .song_feedback_forwarder import (
    SongFeedbackAction,
    SongRecommendationFeedbackEvent,
    emit_song_feedback_event,
)

__all__ = [
    "SongFeedbackAction",
    "SongRecommendationFeedbackEvent",
    "emit_song_feedback_event",
]