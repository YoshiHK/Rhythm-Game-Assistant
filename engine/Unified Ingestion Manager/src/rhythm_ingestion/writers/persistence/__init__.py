"""
writers.persistence

Database persistence layer (lazy load).

Design rules
------------
- no eager imports at package import time
- only expose persistence entrypoints
- safe for verification / orchestration layers
- legacy Excel export remains optional
"""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    # --------------------------------------------------
    # Chart asset writer exports
    # --------------------------------------------------
    if name in {
        "DEFAULT_CHART_ASSET_DB_PATH",
        "open_chart_asset_db",
        "ensure_chart_asset_schema",
        "persist_chart_asset",
        "persist_chart_assets",
        "persist_chart_assets_from_candidates",
        "build_chart_asset_from_file",
        "build_chart_asset_from_reference",
    }:
        from . import chart_asset_writer as mod
        return getattr(mod, name)

    # --------------------------------------------------
    # File scan inventory writer exports
    # --------------------------------------------------
    if name in {
        "open_file_scan_inventory_db",
        "ensure_file_scan_inventory_schema",
        "persist_file_scan_inventory_rows",
        "persist_file_scan_inventory_from_paths",
    }:
        from . import file_scan_inventory_writer as mod
        return getattr(mod, name)

    # --------------------------------------------------
    # Pattern writer exports
    # --------------------------------------------------
    if name in {
        "write_chart_patterns",
        "write_from_rows",
    }:
        from . import chart_pattern_writer as mod
        return getattr(mod, name)

    # --------------------------------------------------
    # Excel writer exports (legacy)
    # --------------------------------------------------
    if name in {
        "ExcelWriter",
        "write_excel_output",
    }:
        from . import excel_writer as mod
        return getattr(mod, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # chart assets
    "DEFAULT_CHART_ASSET_DB_PATH",
    "open_chart_asset_db",
    "ensure_chart_asset_schema",
    "persist_chart_asset",
    "persist_chart_assets",
    "persist_chart_assets_from_candidates",
    "build_chart_asset_from_file",
    "build_chart_asset_from_reference",

    # scan inventory
    "open_file_scan_inventory_db",
    "ensure_file_scan_inventory_schema",
    "persist_file_scan_inventory_rows",
    "persist_file_scan_inventory_from_paths",

    # pattern writer
    "write_chart_patterns",
    "write_from_rows",

    # excel
    "ExcelWriter",
    "write_excel_output",
]