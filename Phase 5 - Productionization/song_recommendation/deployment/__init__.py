"""
Phase 5 — Song Recommendation Learning
Utils Layer (Offline Orchestration)

This package provides orchestration helpers for the offline learning pipeline.

Scope:
- Coordinates aggregation, features, training, evaluation, and artifacts
- Provides entrypoints for running full offline learning cycles

Contract (Non-Negotiable):
- Offline only (Phase 5)
- No runtime usage
- No business logic (delegates to pipeline layers)
- Deterministic execution
- No mutation of pipeline outputs

Updated Guarantees:
- Preserves feature_schema_version across pipeline
- Ensures evaluation is executed before artifact output
- Enforces regression guard awareness

Primary Entry Points:
- run_song_rec_learning_pipeline
- load_feedback_events
"""

from .song_rec_learning_orchestrator import (
    OrchestratorConfig,
    load_feedback_events,
    run_song_rec_learning_pipeline,
)

__all__ = [
    "OrchestratorConfig",
    "load_feedback_events",
    "run_song_rec_learning_pipeline",
]