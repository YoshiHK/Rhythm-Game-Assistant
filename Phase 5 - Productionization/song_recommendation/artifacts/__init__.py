"""
Phase 5 — Song Recommendation Learning
Artifacts Layer (Deployment Boundary)

This package defines how offline learning outputs are exported
as deployment-safe artifacts.

Scope:
- Selector parameter export
- Training report export
- Evaluation report export
- Baseline metrics snapshot

Contract (Non-Negotiable):
- Offline only (Phase 5)
- Outputs are static and deterministic
- Artifacts MUST NOT be used directly in runtime
- No mutation after write

Updated Guarantees:
- All artifacts follow a standard envelope format
- Selector params are minimally validated before export
- Baseline metrics snapshots support regression tracking
- Artifacts are safe for deployment pipelines only

Role in Pipeline:
aggregation → features → training → evaluation → ✅ artifacts → deployment

This is the final boundary before deployment.
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