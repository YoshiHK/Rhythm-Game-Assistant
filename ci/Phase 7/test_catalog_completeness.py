# ci/test_catalog_completeness.py

from rhythm_recommendation.phase7.registry_loader import (
    load_registry_config,
    get_all_games,
)
from rhythm_recommendation.phase7.catalog_loader import (
    load_catalog_config_optional,
    get_all_catalog_entries,
)

def test_catalog_completeness_for_enabled_games():
    """
    CI check: every enabled game must be display-safe.

    A game is considered display-safe if:
    - it has a catalog.json entry, OR
    - it has a non-empty display_name in games.json
    """

    # Load authoritative registry
    reg_cfg = load_registry_config("games.json")
    games = get_all_games(reg_cfg)

    # Load optional catalog metadata
    cat_cfg = load_catalog_config_optional("catalog.json")
    catalog = get_all_catalog_entries(cat_cfg)

    missing = []

    for game_id, meta in games.items():
        status = meta.get("status")
        if status != "enabled":
            continue  # future / ingestion_only are allowed

        registry_name = meta.get("display_name")

        has_catalog = game_id in catalog
        has_registry_name = isinstance(registry_name, str) and registry_name.strip()

        if not has_catalog and not has_registry_name:
            missing.append(game_id)

    assert not missing, (
        "Catalog completeness check failed. "
        "Enabled games missing display metadata: "
        + ", ".join(sorted(missing))
    )
