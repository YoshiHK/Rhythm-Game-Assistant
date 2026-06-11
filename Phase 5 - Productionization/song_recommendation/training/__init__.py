"""
Phase 5 — Song Recommendation Learning
Training Layer (Offline Only)

This package performs **heuristic calibration** for Song Recommendations.

Contract (Non-Negotiable) — per PHASE_5_SONG_RECOMMENDATION_LEARNING_SPEC:
- Offline only (Phase 5).
- No runtime inference or adaptation.
- No gameplay semantics (tips/taxonomy/severity/narrative/localization content).
- Outputs are static parameters introduced via deployment only.
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