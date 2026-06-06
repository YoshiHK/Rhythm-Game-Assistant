"""
Phase 5 — Song Recommendation Learning
Aggregation Layer (Offline Only)

This package aggregates forward-only Song Recommendation feedback events
(emitted in Phase 6) into training-ready, selection-level datasets.

Contract (Non-Negotiable):
- Offline only (Phase 5)
- No runtime dependencies
- No gameplay semantics (tips / taxonomy / severity) as raw aggregation input
- Outputs are deterministic and auditable
- Raw events must remain unchanged
- Derived reasoning, if present, must remain separate from raw feedback

Adjacent Layers:
- Upstream: Phase 6 feedback emission
- Bridge: interpretation_bridge (derived machine hypothesis only)
- Downstream: features / training / evaluation

See README.md for boundaries, invariants, and aggregation rules.
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