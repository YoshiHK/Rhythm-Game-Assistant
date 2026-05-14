"""
Phase 5 — Song Recommendation Learning
Features Layer (Offline Only)

This package converts aggregated, selection-level feedback rows into
training-ready feature rows for heuristic calibration.

Contract (Non-Negotiable):
- Offline only (Phase 5).
- Deterministic transforms (same inputs => same outputs).
- Strictly selection-level; NO gameplay semantics.
- Must not depend on Phase 6 runtime modules.

See README.md for boundaries and invariants.
"""

from .selection_features import (
    FeatureConfig,
    FeatureSummary,
    build_selection_feature_rows,
)

__all__ = [
    "FeatureConfig",
    "FeatureSummary",
    "build_selection_feature_rows",
]