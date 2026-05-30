from __future__ import annotations

"""
rhythm_ingestion.writers package

Writer access layer for the Unified Ingestion Manager (UMI).

Responsibilities:
- Provide a stable factory surface for the orchestration layer
- Expose ExcelWriter for real persistence
- Expose NoOpWriter for dry-run / QA scenarios

This module does NOT:
- perform routing
- perform validation
- contain gameplay semantics
"""

from typing import Any, Dict

from .excel_writer import ExcelWriter


class NoOpWriter:
    """
    No-op / dry-run writer.

    Accepts the same broad interface as a real writer but never writes to disk.
    Intended for:
    - dry-run ingestion
    - QA / validation runs
    - orchestration smoke tests
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.rows = []

    def insert_row(self, *args: Any, **kwargs: Any) -> None:
        self.rows.append({"args": args, "kwargs": kwargs})

    def save(self) -> None:
        return None


# ---------------------------------------------------------------------
# Registry of supported writer kinds
# ---------------------------------------------------------------------

_WRITER_REGISTRY: Dict[str, Any] = {
    "excel": ExcelWriter,
    "noop": NoOpWriter,
    "dry-run": NoOpWriter,
    "dry_run": NoOpWriter,
}


def get_writer(kind: str = "excel", **kwargs: Any) -> Any:
    """
    Factory for writer instances.

    Examples
    --------
    writer = get_writer("excel", db_path="Songs DB.xlsx")
    writer = get_writer("noop")

    Raises
    ------
    KeyError: if the writer kind is unsupported
    """
    key = (kind or "excel").strip().lower()
    if key not in _WRITER_REGISTRY:
        raise KeyError(f"Unsupported writer kind: {kind}")

    cls = _WRITER_REGISTRY[key]
    return cls(**kwargs)


def get_excel_writer(db_path: str, **kwargs: Any) -> ExcelWriter:
    """
    Convenience helper for creating an Excel-backed writer.
    """
    return ExcelWriter(db_path=db_path, **kwargs)


__all__ = [
    "ExcelWriter",
    "NoOpWriter",
    "get_writer",
    "get_excel_writer",
]