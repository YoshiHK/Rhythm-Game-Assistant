"""
rhythm_ingestion.orchestrator_ext.interfaces

Protocols for wrapping an existing orchestrator without modifying it.

This module defines minimal, phase-safe interfaces used by orchestrator_ext.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable


class AdapterProtocol(Protocol):
    game_id: str

    def accepts_file(self, path: Any) -> bool: ...
    def load(self, path: Any) -> Any: ...
    def to_canonical_row(self, raw: Any) -> Dict[str, Any]: ...
    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]: ...
    def capabilities(self) -> dict: ...


class ValidatorProtocol(Protocol):
    game_id: str

    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None: ...

    def capabilities(self) -> dict: ...


@runtime_checkable
class OrchestratorCoreProtocol(Protocol):
    """
    Core orchestrator surface expected by OrchestratorBridge.
    """
    def run(
        self,
        *,
        game_id: str,
        chart_path: str,
        mode: str = "full",
        **kwargs: Any,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class ModuleIngestProtocol(Protocol):
    """
    Legacy module surface supported by OrchestratorBridge via adapter.
    """
    def ingest(
        self,
        source_dir: str,
        *,
        db_path: Optional[str],
        dry_run: bool,
        only_game: Optional[str],
        json_out: Optional[str],
        tips_mode: str,
    ) -> int: ...


@runtime_checkable
class RecommendProtocol(Protocol):
    """
    Optional surface: allows API layer to call orch.recommend(...) safely.
    """
    def recommend(self, **kwargs: Any) -> Dict[str, Any]: ...


__all__ = [
    "AdapterProtocol",
    "ValidatorProtocol",
    "OrchestratorCoreProtocol",
    "ModuleIngestProtocol",
    "RecommendProtocol",
]