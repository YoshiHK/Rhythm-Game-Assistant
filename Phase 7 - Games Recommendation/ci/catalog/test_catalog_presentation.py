# test_catalog_presentation.py

from registry.registry import GameInfo, GameRegistry
from catalog.catalog_loader import load_catalog_config_optional, get_all_catalog_entries



def test_catalog_presentation_helpers_do_not_crash():
    cfg = load_catalog_config_optional()
    entries = get_all_catalog_entries(cfg)
    assert isinstance(entries, dict)
