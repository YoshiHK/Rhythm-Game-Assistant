"""
catalog.py
Phase 7 — Catalog usage examples (NOT core runtime code)

This file demonstrates how to use:
- GameRegistry
- GameCatalog
- catalog_loader helpers

IMPORTANT:
- This module MUST NOT be imported by routing or APIs.
- It is safe as a demo / playground only.
"""

from registry.registry import load_games_registry
from catalog.catalog_loader import (
    load_catalog_config_optional,
)
from .game_catalog import GameCatalog


def demo_catalog_usage() -> None:
    """
    Demonstration of catalog usage patterns.
    """
    registry = load_games_registry("games.json")
    catalog_cfg = load_catalog_config_optional()

    catalog = GameCatalog(registry, catalog_cfg)

    # Public Games Recommendation page
    items = catalog.list_recommendable(locale="en", strict=True)
    print("Public items:", items)

    # Internal admin view
    all_items = catalog.list_all(locale="en")
    print("All items:", all_items)

    # Search support
    hits = catalog.search("arcaea", locale="en")
    print("Search hits:", hits)

    # Debug grouping
    groups = catalog.group_by_status(locale="en")
    print("Grouped by status:", groups)


if __name__ == "__main__":
    demo_catalog_usage()