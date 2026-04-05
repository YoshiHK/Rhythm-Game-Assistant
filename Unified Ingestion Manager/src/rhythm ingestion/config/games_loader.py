from __future__ import annotations

"""
games_loader.py

Loader utilities for config/games.json used by the
Unified Ingestion Manager (UMI), Phase 3.

Responsibilities
----------------
- Load and parse games.json
- Normalize schema differences (list vs dict)
- Provide safe, structured access to game capability metadata
- Remain completely decoupled from adapters, validators, and gameplay logic
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


# Default path relative to this file:
_DEFAULT_GAMES_JSON_PATH = Path(__file__).with_name("games.json")


class GamesConfigError(RuntimeError):
    """Raised when games.json is missing or malformed."""


# ----------------------------------------------------------------------
# Internal normalization
# ----------------------------------------------------------------------

def _normalize_games_node(games_node: Any) -> Dict[str, Dict[str, Any]]:
    """
    Normalize the `games` node to a dict keyed by game_id.

    Accepted forms:
    - dict: { game_id: { ... } }
    - list: [ { "game_id": "...", ... }, ... ]

    Returns:
        Dict[str, Dict[str, Any]]
    """
    if isinstance(games_node, dict):
        # Legacy / already-normalized form
        return games_node

    if isinstance(games_node, list):
        normalized: Dict[str, Dict[str, Any]] = {}
        for entry in games_node:
            if not isinstance(entry, dict):
                raise GamesConfigError("Each entry in games list must be an object")
            game_id = entry.get("game_id")
            if not isinstance(game_id, str) or not game_id:
                raise GamesConfigError("Each game entry must contain a non-empty 'game_id'")
            normalized[game_id] = entry
        return normalized

    raise GamesConfigError("games.json 'games' must be a dict or a list")


# ----------------------------------------------------------------------
# Public loader
# ----------------------------------------------------------------------

def load_games_config(
    path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Load and normalize the raw games.json configuration.

    Parameters
    ----------
    path:
        Optional explicit path to games.json.
        If None, uses the default games.json next to this loader.

    Returns
    -------
    dict
        Parsed and normalized config object with:
        - games: Dict[str, Dict[str, Any]]

    Raises
    ------
    GamesConfigError
        If the file is missing or malformed.
    """
    json_path = Path(path) if path else _DEFAULT_GAMES_JSON_PATH

    if not json_path.exists():
        raise GamesConfigError(f"games.json not found at: {json_path}")

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise GamesConfigError(f"Failed to parse games.json: {exc}") from exc

    if not isinstance(data, dict):
        raise GamesConfigError("games.json root must be a JSON object")

    if "games" not in data:
        raise GamesConfigError("games.json must contain a 'games' field")

    data["games"] = _normalize_games_node(data["games"])
    return data


# ----------------------------------------------------------------------
# Convenience helpers (UMI-facing)
# ----------------------------------------------------------------------

def get_all_games(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Return the full game registry keyed by game_id.
    """
    cfg = config or load_games_config()
    return cfg["games"]


def get_enabled_games(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Return only enabled games.
    """
    games = get_all_games(config)
    return {
        gid: meta
        for gid, meta in games.items()
        if meta.get("status") == "enabled"
    }


def get_games_supporting_tips(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Return games that support tips generation.
    """
    games = get_enabled_games(config)
    return {
        gid: meta
        for gid, meta in games.items()
        if meta.get("tips_generation", {}).get("supported", False)
    }


def get_game_config(
    game_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retrieve configuration for a single game_id.
    Raises KeyError if the game_id is not defined.
    """
    games = get_all_games(config)
    if game_id not in games:
        raise KeyError(f"Unknown game_id in games.json: {game_id}")
    return games[game_id]


def get_supported_extensions(
    game_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Get supported file extensions for a given game.
    """
    game = get_game_config(game_id, config)
    return list(game.get("supported_extensions", []))


__all__ = [
    "GamesConfigError",
    "load_games_config",
    "get_all_games",
    "get_enabled_games",
    "get_games_supporting_tips",
    "get_game_config",
    "get_supported_extensions",
]
