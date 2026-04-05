"""rhythm_ingestion.orchestrator_ext.interfaces

Protocols for wrapping an existing orchestrator without modifying it.
"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class AdapterProtocol(Protocol):
    game_id: str

    def accepts_file(self, path: Any) -> bool: ...
    def load(self, path: Any) -> Any: ...
    def to_canonical_row(self, raw: Any) -> Dict[str, Any]: ...
    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]: ...
    def capabilities(self) -> dict: ...


class ValidatorProtocol(Protocol):
    game_id: str

    def validate(self, *, raw_chart: Any, canonical_payload: Dict[str, Any], canonical_row: Dict[str, Any]) -> None: ...
    def capabilities(self) -> dict: ...


class OrchestratorCoreProtocol(Protocol):
    def run(self, *, game_id: str, chart_path: str, mode: str = "full", **kwargs: Any) -> Dict[str, Any]: ...
