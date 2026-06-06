"""
Phase 5 — Song Recommendation Learning
Features Layer (Offline Only)

This package converts aggregated, selection-level feedback rows into
training-ready feature rows for heuristic calibration.

Contract (Non-Negotiable):
- Offline only (Phase 5)
- Deterministic transforms (same inputs => same outputs)
- Strictly selection-level (no gameplay semantics)
- No dependency on Phase 6 runtime
- No mutation of input rows

Additional Guarantees (UPDATED):
- All outputs are traceable (provenance_id where available)
- Feature schema is versioned (feature_schema_version)
- Derived reasoning (if present) is preserved only as metadata
  and never mixed into core behavioral features

Adjacent Layers:
- Upstream: aggregation (selection-level rows)
- Optional Bridge: interpretation_bridge (derived reasoning)
- Downstream: training, dataset construction, evaluation

See README.md for full contracts and invariants.
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