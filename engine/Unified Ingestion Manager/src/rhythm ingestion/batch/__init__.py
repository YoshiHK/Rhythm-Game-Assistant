from __future__ import annotations

"""
rhythm_ingestion.batch

Multi-game batch orchestration surface for UMI.

Responsibilities:
- expose stable entrypoints for multi-game ingestion runs
- expose stable entrypoints for multi-game QA batch runs
- keep orchestration concerns separate from analysis-only pipeline modules

This package is intended to sit above adapters / validators / writers /
pipeline analysis surfaces and provide a thin orchestration façade.
"""

from .multi_game_ingest import run_ingestion
from .multi_game_batch_qa import run_batch

__all__ = [
    "run_ingestion",
    "run_batch",
]