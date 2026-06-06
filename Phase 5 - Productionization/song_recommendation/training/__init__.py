"""
Phase 5 — Song Recommendation Learning
Training Layer (Offline Only)

This package performs heuristic calibration for Song Recommendations.

It converts selection-level feature rows into static selector parameters
for deployment.

Contract (Non-Negotiable):
- Offline only (Phase 5)
- No runtime inference or adaptation
- No gameplay semantics (tips / taxonomy / severity / narrative / localization)
- Outputs are static and introduced via deployment only
- Deterministic: same inputs => same outputs
- No mutation of inputs

Updated Guarantees:
- Supports feature wrapper input (rows + feature_schema_version)
- Propagates feature_schema_version into training report and params
- All outputs are traceable and auditable
- Compatible with evaluation layer and model validation

Adjacent Layers:
- Upstream: features (selection-level signals)
- Downstream: evaluation, artifact export, deployment
"""

from .train_selector_params import (
    TrainingConfig,
    TrainingReport,
    train_song_selector_params,
    export_song_selector_params_json,
)

__all__ = [
    "TrainingConfig",
    "TrainingReport",
    "train_song_selector_params",
    "export_song_selector_params_json",
]