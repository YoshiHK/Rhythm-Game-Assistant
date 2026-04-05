from rhythm_recommendation.phase7.registry import load_games_registry
from rhythm_recommendation.phase7.game_catalog import GameCatalog

reg = load_games_registry("games.json")
catalog = GameCatalog(reg)

# For the public Games Recommendation page (safe default)
items = catalog.list_recommendable(locale="en", strict=True)

# For an internal “All games” admin view
all_items = catalog.list_all(locale="en")

# Search bar support
hits = catalog.search("arcaea", locale="en")

# Status grouping (useful for debug / admin page)
groups = catalog.group_by_status(locale="en")
