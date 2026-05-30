from __future__ import annotations

"""
rhythm_ingestion.pipeline

Semantic analysis pipeline for rhythm game charts.

This package defines the analysis layer that operates on canonical
chart payloads produced by the Unified Ingestion Manager (UMI).

It exposes stable, game-agnostic analysis components for:
- section-level metrics
- pattern tag semantics
- per-chart and batch-level tips analysis

This package MUST NOT:
- perform ingestion or file I/O
- invoke adapters or validators
- contain CLI or orchestration logic
- depend on UMI implementation details
"""

# ---------------------------------------------------------------------
# Sub-pipelines (stable public surfaces)
# ---------------------------------------------------------------------

from . import section_metrics  # noqa: F401
from . import pattern_tags     # noqa: F401
from . import tips             # noqa: F401

__all__ = [
    "section_metrics",
    "pattern_tags",
    "tips",
]