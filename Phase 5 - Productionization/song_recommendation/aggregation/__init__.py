"""
Phase 5 — Song Recommendation Learning
Aggregation Layer (Offline Only)

This package aggregates forward-only Song Recommendation feedback events
(emitted in Phase 6) into training-ready, selection-level datasets.

Contract (Non-Negotiable):
- Offline only (Phase 5).
- No runtime dependencies.
- No gameplay semantics (tips/taxonomy/severity) allowed.
- Outputs are deterministic and auditable.

See README.md for boundaries and invariants.
"""

from .aggregate_song_feedback import (
    AggregationConfig,
    AggregationSummary,
    aggregate_song_feedback_events,
)

__all__ = [
    "AggregationConfig",
    "AggregationSummary",
    "aggregate_song_feedback_events",
]