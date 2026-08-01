"""
writers.bridges

Pipeline wiring / glue layer between ingestion, analysis, and feedback.
"""

from .chart_feature_bridge import (
    build_chart_feature_rows,
)

from .song_identity_resolver import (
    resolve_song_identity,
)

from .feedback_event_adapter import (
    adapt_feedback_event,
)

from .feedback_event_provenance import (
    stamp_feedback_provenance,
)

__all__ = [
    "build_chart_feature_rows",
    "resolve_song_identity",
    "adapt_feedback_event",
    "stamp_feedback_provenance",
]