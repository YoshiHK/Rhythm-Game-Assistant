# test_catalog_presentation.py

from rhythm_recommendation.phase7.registry import GameInfo, GameRegistry
from rhythm_recommendation.phase7.game_catalog import GameCatalog


def test_catalog_basic_operations_do_not_crash():
    """
    Presentation helpers must not crash on minimal registry input.
    """
    reg = GameRegistry(
        games=[
            GameInfo(game_id="test_game", status="enabled", display_name="Test Game")
        ]
    )

    catalog = GameCatalog(registry=reg, catalog_config={"catalog": {}})

    # list
    items = catalog.list_recommendable(locale="en", strict=True)
    assert isinstance(items, list)

    # search
    hits = catalog.search("test", locale="en")
    assert isinstance(hits, list)

    # grouping
    groups = catalog.group_by_status(locale="en")
    assert isinstance(groups, dict)