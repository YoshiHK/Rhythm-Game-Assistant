"""
Phase 5 — Song Recommendation Learning
Artifacts Layer (Offline Only)

This package writes and loads **offline artifacts** produced by Phase 5:
- static selector parameter JSON (deployment artifact)
- training reports
- evaluation reports + baseline snapshots

Contract (Non-Negotiable) — per PHASE_5_SONG_RECOMMENDATION_LEARNING_SPEC:
- Offline only (Phase 5).
- Deterministic artifact serialization.
- No runtime dependencies on Phase 6.
- Artifacts are introduced via deployment only (Phase 6 MUST NOT load dynamically).
"""

from .artifact_exporter import (
    ArtifactPaths,
    write_song_selector_params,
    write_training_report,
    write_evaluation_report,
    write_baseline_metrics_snapshot,
    load_baseline_metrics_snapshot,
)

__all__ = [
    "ArtifactPaths",
    "write_song_selector_params",
    "write_training_report",
    "write_evaluation_report",
    "write_baseline_metrics_snapshot",
    "load_baseline_metrics_snapshot",
]