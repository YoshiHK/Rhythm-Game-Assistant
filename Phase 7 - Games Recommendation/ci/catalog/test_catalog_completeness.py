# test_catalog_completeness.py

from rhythm_recommendation.phase7.catalog_loader import (
    load_catalog_config_optional,
    get_all_catalog_entries,
)


def test_catalog_optional_loading():
    """
    Catalog is optional.
    Absence of catalog.json must not break Phase 7.
    """
    cfg = load_catalog_config_optional()
    assert isinstance(cfg, dict)
    assert "catalog" in cfg
    assert isinstance(cfg["catalog"], dict)


def test_catalog_entries_keyed_by_game_id():
    """
    If catalog entries exist, they must be keyed by game_id (str).
    """
    cfg = load_catalog_config_optional()
    entries = get_all_catalog_entries(cfg)
    for k, v in entries.items():
        assert isinstance(k, str)
        assert isinstance(v, dict)