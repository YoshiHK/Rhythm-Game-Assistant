from pathlib import Path

pkg = Path('rhythm_recommendation/phase7')
pkg.mkdir(parents=True, exist_ok=True)

code = '''from __future__ import annotations
"""registry_loader.py

Loader utilities for the authoritative <File>games.json</File> used by Phase 7
(Games Recommendations).

This module intentionally mirrors the structure and style of Phase 3's
<File>games_loader.py</File>:
- load and parse games.json
- normalize schema differences (list vs dict)
- provide safe, structured access to game registry metadata
- remain completely decoupled from ranking, explanations, and gameplay logic

Phase 7 constraints:
- downstream-only and read-only
- MUST NOT modify completed phases
- MUST NOT hardcode games; <File>games.json</File> is the single source of truth
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# Default path relative to this file (Phase 7 package):
_DEFAULT_GAMES_JSON_PATH = Path(__file__).with_name('games.json')


class RegistryConfigError(RuntimeError):
    """Raised when games.json is missing or malformed for Phase 7."""


# ----------------------------------------------------------------------
# Internal normalization
# ----------------------------------------------------------------------

def _normalize_games_node(games_node: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize the `games` node to a dict keyed by game_id.

    Accepted forms:
    - dict: { game_id: { ... } }
    - list: [ {"game_id": "...", ...}, ... ]

    Returns:
        Dict[str, Dict[str, Any]]
    """
    if isinstance(games_node, dict):
        # Already-normalized form
        return games_node

    if isinstance(games_node, list):
        normalized: Dict[str, Dict[str, Any]] = {}
        for entry in games_node:
            if not isinstance(entry, dict):
                raise RegistryConfigError('Each entry in games list must be an object')
            game_id = entry.get('game_id')
            if not isinstance(game_id, str) or not game_id:
                raise RegistryConfigError("Each game entry must contain a non-empty 'game_id'")
            normalized[game_id] = entry
        return normalized

    raise RegistryConfigError("games.json 'games' must be a dict or a list")


# ----------------------------------------------------------------------
# Public loader
# ----------------------------------------------------------------------

def load_registry_config(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load and normalize the raw games.json configuration for Phase 7.

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
    RegistryConfigError
        If the file is missing or malformed.
    """
    json_path = Path(path) if path else _DEFAULT_GAMES_JSON_PATH
    if not json_path.exists():
        raise RegistryConfigError(f'games.json not found at: {json_path}')

    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as exc:
        raise RegistryConfigError(f'Failed to parse games.json: {exc}') from exc

    if not isinstance(data, dict):
        raise RegistryConfigError('games.json root must be a JSON object')
    if 'games' not in data:
        raise RegistryConfigError("games.json must contain a 'games' field")

    data['games'] = _normalize_games_node(data['games'])
    return data


# ----------------------------------------------------------------------
# Convenience helpers (Phase-7-facing)
# ----------------------------------------------------------------------

def get_all_games(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Return the full game registry keyed by game_id."""
    cfg = config or load_registry_config()
    return cfg['games']


def get_enabled_games(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Return only games with status == 'enabled'."""
    games = get_all_games(config)
    return {gid: meta for gid, meta in games.items() if meta.get('status') == 'enabled'}


def get_recommendable_games(
    config: Optional[Dict[str, Any]] = None,
    *,
    strict: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Return games allowed to appear in Phase 7 recommendations.

    strict=True  -> status == 'enabled'
    strict=False -> status in {'enabled', 'ingestion_only'} (useful for internal/testing)

    NOTE: This is a registry-only gate. Ranking and user constraints belong
    to the Phase 7 ranker/router.
    """
    games = get_all_games(config)
    if strict:
        allowed = {'enabled'}
    else:
        allowed = {'enabled', 'ingestion_only'}
    return {gid: meta for gid, meta in games.items() if meta.get('status') in allowed}


def get_game_config(game_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve configuration for a single game_id.

    Raises KeyError if the game_id is not defined.
    """
    games = get_all_games(config)
    if game_id not in games:
        raise KeyError(f'Unknown game_id in games.json: {game_id}')
    return games[game_id]


__all__ = [
    'RegistryConfigError',
    'load_registry_config',
    'get_all_games',
    'get_enabled_games',
    'get_recommendable_games',
    'get_game_config',
]
'''

(pkg / 'registry_loader.py').write_text(code, encoding='utf-8')

# Add exports to __init__.py (additive)
init_path = pkg / '__init__.py'
init_txt = init_path.read_text(encoding='utf-8') if init_path.exists() else ''
if 'registry_loader' not in init_txt:
    init_txt += "\nfrom .registry_loader import (\n    RegistryConfigError,\n    load_registry_config,\n    get_all_games,\n    get_enabled_games,\n    get_recommendable_games,\n    get_game_config,\n)\n"
    init_path.write_text(init_txt, encoding='utf-8')

print('Created rhythm_recommendation/phase7/registry_loader.py')
