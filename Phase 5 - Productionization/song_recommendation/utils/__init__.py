"""
Phase 5 — Song Recommendation Learning
Utils / Orchestrator Helper (Offline Only)

This package provides an offline helper to run the learning dataflow:
feedback -> aggregation -> features -> training -> evaluation -> artifacts.

Contract (Non-Negotiable):
- Offline only (Phase 5).
- Not a runtime decision engine. [1](https://onedrive.live.com/?id=1e428acc-4a68-416e-9d6d-c8692b153f2c&cid=d5d62a1ef303ba22&web=1)
- Must not modify completed semantic phases. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)
- Outputs are deployment artifacts only. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)
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