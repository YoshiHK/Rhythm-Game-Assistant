"""
rhythm_ingestion

Unified Ingestion Manager (UMI) for rhythm game chart analysis.

This package defines the Phase 3 ingestion layer responsible for:
- routing chart inputs to the correct game adapter
- producing canonical rows and canonical payloads
- validating canonical data via game-specific validators
- invoking downstream semantic analysis pipelines (Phase 1–2)

This package MUST NOT:
- contain gameplay analysis logic (see rhythm_ingestion.pipeline)
- generate tips or narratives directly
- perform batch QA or CLI orchestration
- embed game-specific semantics

Primary entry point:
- orchestrator.py
"""

from __future__ import annotations

__all__ = [
    "orchestrator",
]
