"""
rhythm_ingestion.config

Configuration access layer for the Unified Ingestion Manager (UMI).

This module is responsible for loading static configuration files such as:
- games.json
- adapters.json

It does NOT perform any routing, validation, or instantiation logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

_CONFIG_DIR = Path(__file__).parent
_GAMES_JSON = _CONFIG_DIR / "games.json"
_ADAPTERS_JSON = _CONFIG_DIR / "adapters.json"


# ---------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------

def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8 as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a JSON object")
    return data


# ---------------------------------------------------------------------
# Loaded configs (module-level, read-only)
# ---------------------------------------------------------------------

_GAMES_CONFIG: Dict[str, Any] = _load_json(_GAMES_JSON)
_ADAPTERS_CONFIG: Dict[str, Any] = _load_json(_ADAPTERS_JSON)


# ---------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------

def get_games_config() -> Dict[str, Any]:
    """
    Return the full games.json configuration.
    """
    return _GAMES_CONFIG


def get_adapters_config() -> Dict[str, Any]:
    """
    Return the full adapters.json configuration.
    """
    return _ADAPTERS_CONFIG


def get_game_entry(game_id: str) -> Dict[str, Any]:
    """
    Return a single game entry from games.json.

    Raises KeyError if the game_id is not declared.
    """
    games = _GAMES_CONFIG.get("games", {})
    if game_id not in games:
        raise KeyError(f"Game not declared in games.json: {game_id}")
    return games[game_id]


def get_adapter_entry(game_id: str) -> Dict[str, Any]:
    """
    Return a single adapter entry from adapters.json.

    Raises KeyError if the game_id is not declared.
    """
    if game_id not in _ADAPTERS_CONFIG:
        raise KeyError(f"Adapter not declared in adapters.json: {game_id}")
    return _ADAPTERS_CONFIG[game_id]


__all__ = [
    "get_games_config",
    "get_adapters_config",
    "get_game_entry",
    "get_adapter_entry",
]
``
