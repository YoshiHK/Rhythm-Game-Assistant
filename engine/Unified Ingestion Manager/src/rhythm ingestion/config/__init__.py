from __future__ import annotations

"""
rhythm_ingestion.config
Configuration access layer for the Unified Ingestion Manager (UMI).

This module is responsible for loading static configuration files such as:
- games.json

It does NOT perform routing, validation, adapter instantiation, or gameplay logic.
"""

import json
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).parent
_GAMES_JSON = _CONFIG_DIR / "games.json"


# ---------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a JSON object")

    return data


# ---------------------------------------------------------------------
# Loaded configs (module-level, read-only)
# ---------------------------------------------------------------------

_GAMES_CONFIG: Dict[str, Any] = _load_json(_GAMES_JSON)


# ---------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------

def get_games_config() -> Dict[str, Any]:
    """
    Return the full games.json configuration.
    """
    return _GAMES_CONFIG


def get_game_entry(game_id: str) -> Dict[str, Any]:
    """
    Return a single game entry from games.json by game_id.

    Raises KeyError if the requested game_id does not exist.
    """
    games = _GAMES_CONFIG.get("games") or []
    for entry in games:
        if isinstance(entry, dict) and entry.get("game_id") == game_id:
            return entry
    raise KeyError(f"Game entry not found for game_id: {game_id}")


__all__ = [
    "get_games_config",
    "get_game_entry",
]