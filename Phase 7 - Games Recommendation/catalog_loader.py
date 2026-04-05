from pathlib import Path

pkg = Path('rhythm_recommendation/phase7')
pkg.mkdir(parents=True, exist_ok=True)

code = '''from __future__ import annotations
"""catalog_loader.py

Loader utilities for Phase 7 *presentation metadata*.

This module mirrors the structure and style of Phase 3's games_loader.py:
- load and parse catalog.json (Phase 7 UI catalog metadata)
- normalize schema differences (list vs dict)
- provide safe, structured access to catalog metadata keyed by game_id
- remain completely decoupled from ranking, explanations, and gameplay logic

Relationship to games.json:
- <File>games.json</File> remains the single source of truth for game identity and status.
- catalog.json is OPTIONAL and additive: it provides UI-facing metadata such as
  icons, store links, and localized display overrides.

Phase 7 constraints:
- downstream-only and read-only
- MUST NOT modify completed phases
- MUST NOT hardcode games
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Default path relative to this file (Phase 7 package)
_DEFAULT_CATALOG_JSON_PATH = Path(__file__).with_name('catalog.json')


class CatalogConfigError(RuntimeError):
    """Raised when catalog.json is missing or malformed."""


# ----------------------------------------------------------------------
# Internal normalization
# ----------------------------------------------------------------------

def _normalize_catalog_node(node: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize the `catalog` node to a dict keyed by game_id.

    Accepted forms:
    - dict: { game_id: { ... } }
    - list: [ {"game_id": "...", ...}, ... ]

    Returns:
        Dict[str, Dict[str, Any]]
    """
    if isinstance(node, dict):
        return node

    if isinstance(node, list):
        normalized: Dict[str, Dict[str, Any]] = {}
        for entry in node:
            if not isinstance(entry, dict):
                raise CatalogConfigError('Each entry in catalog list must be an object')
            game_id = entry.get('game_id')
            if not isinstance(game_id, str) or not game_id:
                raise CatalogConfigError("Each catalog entry must contain a non-empty 'game_id'")
            normalized[game_id] = entry
        return normalized

    raise CatalogConfigError("catalog.json 'catalog' must be a dict or a list")


# ----------------------------------------------------------------------
# Public loader
# ----------------------------------------------------------------------

def load_catalog_config(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load and normalize the raw catalog.json configuration.

    Parameters
    ----------
    path:
        Optional explicit path to catalog.json.
        If None, uses the default catalog.json next to this loader.

    Returns
    -------
    dict
        Parsed and normalized config object with:
        - catalog: Dict[str, Dict[str, Any]]

    Raises
    ------
    CatalogConfigError
        If the file is missing or malformed.

    Notes
    -----
    catalog.json is optional in the product; callers may choose to treat missing
    file as an empty catalog by using :func:`load_catalog_config_optional`.
    """
    json_path = Path(path) if path else _DEFAULT_CATALOG_JSON_PATH
    if not json_path.exists():
        raise CatalogConfigError(f'catalog.json not found at: {json_path}')

    try:
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as exc:
        raise CatalogConfigError(f'Failed to parse catalog.json: {exc}') from exc

    if not isinstance(data, dict):
        raise CatalogConfigError('catalog.json root must be a JSON object')
    if 'catalog' not in data:
        raise CatalogConfigError("catalog.json must contain a 'catalog' field")

    data['catalog'] = _normalize_catalog_node(data['catalog'])
    return data


def load_catalog_config_optional(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Load catalog.json but fall back to an empty catalog if missing.

    This helper is designed for Phase 7 early rollout where catalog metadata
    may not exist yet.
    """
    json_path = Path(path) if path else _DEFAULT_CATALOG_JSON_PATH
    if not json_path.exists():
        return {'_meta': {'description': 'optional catalog', 'notes': 'file missing; using empty catalog'}, 'catalog': {}}
    return load_catalog_config(json_path)


# ----------------------------------------------------------------------
# Convenience helpers (UI-facing)
# ----------------------------------------------------------------------

def get_all_catalog_entries(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Return the full catalog registry keyed by game_id."""
    cfg = config or load_catalog_config_optional()
    return cfg.get('catalog', {})


def get_catalog_entry(game_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve catalog entry for a single game_id.

    Raises KeyError if the game_id is not defined in catalog.
    """
    catalog = get_all_catalog_entries(config)
    if game_id not in catalog:
        raise KeyError(f'Unknown game_id in catalog.json: {game_id}')
    return catalog[game_id]


def get_display_overrides(game_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return display override metadata for a game.

    Expected (optional) shapes inside each catalog entry:
    - display: { default: str, i18n: { "en": str, ... } }
    - icon: { ... }
    - links: { app_store: str, google_play: str, official: str, ... }

    This function does not enforce schema beyond dict-ness.
    """
    entry = get_catalog_entry(game_id, config)
    display = entry.get('display')
    return display if isinstance(display, dict) else {}


# ----------------------------------------------------------------------
# Optional cross-checks against games.json (wiring-only)
# ----------------------------------------------------------------------

def diff_games_vs_catalog(
    *,
    games: Dict[str, Dict[str, Any]],
    catalog: Dict[str, Dict[str, Any]],
) -> Tuple[Set[str], Set[str]]:
    """Return (missing_in_catalog, extra_in_catalog).

    This helper is *wiring-only* and does not decide which games should be recommended.
    """
    gset = set(games.keys())
    cset = set(catalog.keys())
    return (gset - cset, cset - gset)


__all__ = [
    'CatalogConfigError',
    'load_catalog_config',
    'load_catalog_config_optional',
    'get_all_catalog_entries',
    'get_catalog_entry',
    'get_display_overrides',
    'diff_games_vs_catalog',
]
'''

(pkg / 'catalog_loader.py').write_text(code, encoding='utf-8')

# Export from __init__.py (additive)
init_path = pkg / '__init__.py'
init_txt = init_path.read_text(encoding='utf-8') if init_path.exists() else ''
if 'catalog_loader' not in init_txt:
    init_txt += "\nfrom .catalog_loader import (\n    CatalogConfigError,\n    load_catalog_config,\n    load_catalog_config_optional,\n    get_all_catalog_entries,\n    get_catalog_entry,\n    get_display_overrides,\n    diff_games_vs_catalog,\n)\n"
    init_path.write_text(init_txt, encoding='utf-8')

print('Created rhythm_recommendation/phase7/catalog_loader.py')
