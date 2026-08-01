# presentation/game_panels.py
# UI-facing helpers for game capability panels

from typing import Dict, Any, Optional
from config.games_loader import get_game_config, load_games_config
from presentation.badges import get_status_badge, get_capability_badge


def use_game_badges(
    game_id: str,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Return UI-ready badge payload for a game.

    Output:
    {
        "game_id": "...",
        "display_name": "...",
        "badges": {
            "overall": {label,color,value},
            "capabilities": {
                "adapter": {...},
                "validator": {...},
                ...
            }
        }
    }
    """
    cfg = config or load_games_config()
    meta = get_game_config(game_id, cfg)

    overall_value = meta.get("overall_status", "")
    overall = get_status_badge(overall_value)
    overall["value"] = str(overall_value).lower()

    caps_out = {}
    caps = meta.get("capabilities", {})
    if isinstance(caps, dict):
        for k, v in caps.items():
            badge = get_capability_badge(v)
            badge["value"] = str(v).lower()
            caps_out[k] = badge

    return {
        "game_id": meta.get("game_id", game_id),
        "display_name": meta.get("display_name", game_id),
        "badges": {
            "overall": overall,
            "capabilities": caps_out,
        },
    }