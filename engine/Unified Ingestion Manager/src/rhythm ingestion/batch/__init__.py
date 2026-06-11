"""
Batch module exports (Phase 3 wiring layer)

Purpose:
- provide stable entrypoints for ingestion
- keep routing + orchestration decoupled
"""

from __future__ import annotations

from .multi_game_ingest import run_ingestion

def get_batch_runner():
    """
    Factory wrapper (flexible routing entry)
    """
    return run_ingestion


__all__ = [
    "run_ingestion",
    "get_batch_runner",
]