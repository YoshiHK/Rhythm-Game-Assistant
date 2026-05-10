"""
Phase 7 — Catalog Layer

Presentation-only helpers for games metadata.

This package MUST NOT:
- influence ranking or routing
- implement eligibility logic
- perform locale normalization
- introduce runtime side effects
"""

from .catalog_loader import (
    CatalogConfigError,
    load_catalog_config,
    load_catalog_config_optional,
    get_all_catalog_entries,
    get_catalog_entry,
    get_display_overrides,
    diff_games_vs_catalog,
)

__all__ = [
    "CatalogConfigError",
    "load_catalog_config",
    "load_catalog_config_optional",
    "get_all_catalog_entries",
    "get_catalog_entry",
    "get_display_overrides",
    "diff_games_vs_catalog",
]