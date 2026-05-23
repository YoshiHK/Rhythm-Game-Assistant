"""
Phase 7 CI — Catalog Presentation Helpers (Design-Locked)

Purpose:
- Presentation helpers must not crash on minimal/empty catalog config.

Non-goals:
- Does NOT validate catalog.json presence
- Does NOT validate UI fields correctness
"""

from catalog.catalog_loader import (
    load_catalog_config_optional,
    get_all_catalog_entries,
    get_catalog_entry,
    get_display_overrides,
)


def test_catalog_presentation_helpers_do_not_crash():
    cfg = load_catalog_config_optional()
    entries = get_all_catalog_entries(cfg)

    assert isinstance(entries, dict), "entries must be a dict"

    # The following must be safe even if catalog is empty
    _ = get_catalog_entry("non_existent_game", cfg)
    _ = get_display_overrides("non_existent_game", cfg)