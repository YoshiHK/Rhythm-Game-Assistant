"""
writers

Unified ingestion writer layer (lightweight public API).

Design goals
------------
- keep package import lightweight
- avoid eager imports at package import time
- preserve backward compatibility for older orchestrator code
- allow subpackages (e.g. normalizers) to be imported independently
"""

from __future__ import annotations

from typing import Any


# --------------------------------------------------
# Backward-compatible writer routing shim
# --------------------------------------------------
def get_writer(kind: str = "legacy"):
    """
    Backward-compatible writer lookup.

    Legacy Phase 3 orchestrator expects:
        writer = get_writer()
        writer.write_rows(rows, db_path=...)

    Therefore:
    - default kind='legacy' returns an ExcelWriter instance
    - newer additive routes remain available via explicit kind
    """

    # --------------------------------------------------
    # Legacy writer contract (default)
    # --------------------------------------------------
    if kind in {"legacy", "song_db", "excel"}:
        try:
            from .persistence.excel_writer import ExcelWriter
        except ImportError:
            try:
                from excel_writer import ExcelWriter  # flat fallback
            except ImportError as e:
                raise RuntimeError(
                    "Legacy Excel writer could not be imported."
                ) from e

        return ExcelWriter()

    # --------------------------------------------------
    # New additive asset pipeline routes
    # --------------------------------------------------
    if kind in {"asset", "chart_asset"}:
        from .orchestrators.chart_asset_ingestion_orchestrator import (
            ingest_chart_assets,
        )
        return ingest_chart_assets

    if kind == "asset_from_scan":
        from .orchestrators.chart_asset_ingestion_orchestrator import (
            ingest_chart_assets_from_file_scan_candidates,
        )
        return ingest_chart_assets_from_file_scan_candidates

    raise KeyError(f"Unknown writer kind: {kind}")


# --------------------------------------------------
# Optional lazy exports for compatibility
# --------------------------------------------------
def __getattr__(name: str) -> Any:
    if name == "ingest_chart_assets":
        from .orchestrators.chart_asset_ingestion_orchestrator import (
            ingest_chart_assets,
        )
        return ingest_chart_assets

    if name == "ingest_chart_assets_from_file_scan_candidates":
        from .orchestrators.chart_asset_ingestion_orchestrator import (
            ingest_chart_assets_from_file_scan_candidates,
        )
        return ingest_chart_assets_from_file_scan_candidates

    if name == "classify_chart_asset_candidate":
        from .classifiers.chart_asset_classifier import (
            classify_chart_asset_candidate,
        )
        return classify_chart_asset_candidate

    if name == "validate_chart_asset_candidate":
        from .validators.validation.chart_asset_validator import (
            validate_chart_asset_candidate,
        )
        return validate_chart_asset_candidate

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "get_writer",
    "ingest_chart_assets",
    "ingest_chart_assets_from_file_scan_candidates",
    "classify_chart_asset_candidate",
    "validate_chart_asset_candidate",
]