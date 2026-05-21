"""
Phase 7 CI — Catalog Completeness (Design-Locked)

Catalog is OPTIONAL.
Absence of catalog.json MUST NOT break Phase 7.

Non-goals:
- Does NOT require catalog.json to exist
- Does NOT validate catalog content quality
"""

from catalog.catalog_loader import (
    load_catalog_config_optional,
    get_all_catalog_entries,
)


def test_catalog_optional_loading():
    """
    Catalog is optional.
    Absence of catalog.json must not break Phase 7.
    """
    cfg = load_catalog_config_optional()

    assert isinstance(cfg, dict), "catalog config must be a dict"
    assert "catalog" in cfg, "catalog config must contain 'catalog' key"
    assert isinstance(cfg["catalog"], dict), "cfg['catalog'] must be a dict"


def test_catalog_entries_keyed_by_game_id():
    """
    If catalog entries exist, they must be keyed by game_id (str),
    and each entry value must be a dict (presentation metadata).
    """
    cfg = load_catalog_config_optional()
    entries = get_all_catalog_entries(cfg)

    assert isinstance(entries, dict), "catalog entries must be a dict"

    for k, v in entries.items():
        assert isinstance(k, str), f"catalog key must be str, got {type(k)}"
        assert isinstance(v, dict), f"catalog entry must be dict, got {type(v)}"