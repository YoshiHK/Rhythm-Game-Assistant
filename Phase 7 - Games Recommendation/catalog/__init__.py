"""
Phase 7 — Catalog package (presentation-only, optional)

Design:
- Optional metadata layer (catalog.json)
- Must NEVER affect ranking / routing
- Safe for CI usage
"""

from .catalog_loader import (
    load_catalog_config,
    load_catalog_config_optional,
    get_all_catalog_entries,
    get_catalog_entry,
    get_display_overrides,
)

__all__ = [
    "load_catalog_config",
    "load_catalog_config_optional",
    "get_all_catalog_entries",
    "get_catalog_entry",
    "get_display_overrides",
]