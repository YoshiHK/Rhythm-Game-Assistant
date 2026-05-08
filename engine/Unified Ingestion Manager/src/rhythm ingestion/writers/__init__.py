"""
Writers package for the Unified Ingestion Manager.

This module exposes a small, explicit factory over concrete writer
implementations (currently an Excel-backed writer and a no-op writer
for dry-run / QA scenarios).

Primary responsibilities
------------------------
- Provide a stable interface for the ingestion pipeline to obtain a writer
  instance (e.g. for the unified Songs DB Excel workbook).
- Hide implementation details of individual writers (e.g. `ExcelWriter`).
- Be easy to extend with new output formats in Phase 3+ (JSON, CSV, cloud, etc.).

Current implementations
-----------------------
- ExcelWriter
    Writes canonical song rows into an existing Excel workbook, with one
    worksheet per game. See `excel_writer.py` for details.

- NoOpWriter
    A dry-run writer that accepts the same interface as `ExcelWriter`
    but never touches the filesystem. Intended for QA / validation runs
    where you want to exercise the ingestion pipeline and validators
    without mutating the Songs DB.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from .excel_writer import ExcelWriter  # noqa: F401  (re-export for convenience)


class NoOpWriter:
    """
    No-op / dry-run writer.

    This writer implements the minimal interface expected from concrete
    writers:

        - __init__(...)
        - insert_row(game_id, canonical_row)
        - save()

    but it never writes to disk.

    Instead, it optionally keeps an in-memory log of the rows that would
    have been written. This is useful for QA tooling or unit tests that
    want to inspect what the ingestion pipeline produced without modifying
    the canonical Excel Songs DB.

    Parameters
    ----------
    capture_rows :
        If True (default), the writer stores all rows passed to `insert_row`
        in memory under `self.rows`. If False, rows are ignored entirely.
    """

    def __init__(self, capture_rows: bool = True, **_: Any) -> None:
        # Rows are stored as a list of (game_id, canonical_row_dict).
        self.capture_rows: bool = capture_rows
        self.rows: List[tuple[str, MutableMapping[str, Any]]] = []

    # Public API ---------------------------------------------------------

    def insert_row(self, game_id: str, canonical_row: Mapping[str, Any]) -> None:
        """
        Accept a canonical row for a given game, but do not persist it.

        Parameters
        ----------
        game_id:
            Game identifier (e.g. "proseka", "arcaea", "bandori").
        canonical_row:
            Canonical song row dict. This is accepted for interface
            compatibility but is not written to disk.

        Notes
        -----
        If `capture_rows` is True, a shallow copy of `canonical_row`
        is stored in `self.rows` for later inspection by tests / QA tools.
        """
        if not self.capture_rows:
            return

        # Store a shallow copy to decouple from caller mutations.
        self.rows.append((game_id, dict(canonical_row)))

    def save(self) -> None:
        """
        No-op.

        Provided for interface compatibility with writers that persist data
        (e.g. ExcelWriter). Calling this method is safe and has no side effects.
        """
        # Intentionally do nothing.
        return

    # Helpers -----------------------------------------------------------

    def get_rows(self) -> List[tuple[str, MutableMapping[str, Any]]]:
        """
        Retrieve the captured rows as a list of (game_id, canonical_row) tuples.

        This is primarily intended for tests or QA tooling that want to
        inspect which rows would have been written during a dry-run.
        """
        return list(self.rows)


# Registry of supported writer kinds.
# Keys are simple, human-readable identifiers used by the ingestion pipeline
# or configuration; values are the concrete writer classes.
_WRITER_REGISTRY: Dict[str, Any] = {
    "excel": ExcelWriter,
    "noop": NoOpWriter,
    "dry-run": NoOpWriter,
    "dry_run": NoOpWriter,
}


def get_writer(kind: str = "excel", **kwargs: Any) -> Any:
    """
    Factory for writer instances.

    Parameters
    ----------
    kind:
        Identifier for the writer type. Currently supported:
        - "excel": Excel-backed writer (see `ExcelWriter`).
        - "noop", "dry-run", "dry_run": No-op writer (see `NoOpWriter`),
          which performs no filesystem writes.
    **kwargs:
        Arbitrary keyword arguments forwarded to the writer constructor.
        For the Excel writer, the most important parameters are:
        - db_path: str
            Path to the Excel workbook (e.g. "Song Database (full).xlsx").
          Any other kwargs are passed through directly to `ExcelWriter`.

        For the NoOp writer:
        - capture_rows: bool (default True)
            Whether to store rows passed into `insert_row` in memory.

    Returns
    -------
    writer:
        An instance of the requested writer type.

    Raises
    ------
    ValueError
        If `kind` is not registered in `_WRITER_REGISTRY`.

    Examples
    --------
    Excel-backed pipeline:

        from rhythm_ingestion.writers import get_writer

        writer = get_writer(
            kind="excel",
            db_path="Song Database (full).xlsx",
        )
 writer.insert_row(game_id="proseka", canonical_row=row_dict)
        writer.save()

    Dry-run / QA pipeline:

        writer = get_writer(kind="noop")
        writer.insert_row("proseka", canonical_row)
        writer.save()  # no-op

        # Optionally inspect:
        rows = writer.get_rows()
    """
    kind_normalized = (kind or "").lower()
    if kind_normalized not in _WRITER_REGISTRY:
        raise ValueError(f"Unsupported writer kind: {kind!r}")

    writer_cls = _WRITER_REGISTRY[kind_normalized]
    return writer_cls(**kwargs)


def get_excel_writer(db_path: str, **kwargs: Any) -> ExcelWriter:
    """
    Convenience helper for creating an Excel-backed writer.

    Parameters
    ----------
    db_path:
        Path to the Excel workbook backing the unified Songs DB.
    **kwargs:
        Additional keyword arguments forwarded to `ExcelWriter`.

    Returns
    -------
    ExcelWriter
        A configured Excel writer instance.

    Examples
    --------
        from rhythm_ingestion.writers import get_excel_writer

        writer = get_excel_writer("Song Database (full).xlsx")
        writer.insert_row("proseka", canonical_row)
        writer.save()
    """
    return ExcelWriter(db_path=db_path, **kwargs)
