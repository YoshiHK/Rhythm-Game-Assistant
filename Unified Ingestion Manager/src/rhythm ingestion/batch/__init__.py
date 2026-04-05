"""
rhythm_ingestion.pipeline.batch

Batch-level analysis utilities for the gameplay analysis pipeline.

This package contains logic that operates on *collections of charts*,
typically grouped by:
- game_id
- difficulty_label
- ingestion batch

It is responsible for:
- aggregating per-chart summaries
- producing batch-level summary blocks
- exposing stable data structures for downstream consumers
  (QA, analytics, recommendation engine)

This package MUST NOT:
- perform file I/O
- run adapters or validators
- contain CLI logic
- depend on ingestion orchestration
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# Batch summary builders
# ---------------------------------------------------------------------
from rhythm_ingestion.pipeline.tips import build_batch_summary  # re-export

# ---------------------------------------------------------------------
# Batch summary schemas / dataclasses
# ---------------------------------------------------------------------
from rhythm_ingestion.pipeline.tips.proseka_batch_summary_dataclasses import (  # noqa: F401
    BatchLevelSummary,
    ScoreDistribution,
    TopElement,
    TipsCompliance,
)

__all__ = [
    # builders
    "build_batch_summary",
    # schemas
    "BatchLevelSummary",
    "ScoreDistribution",
    "TopElement",
    "TipsCompliance",
]
