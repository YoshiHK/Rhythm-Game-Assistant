from __future__ import annotations

"""
catalog_loaderPhase 7 — Catalog Loader (presentation metadata only)catalog_loader.py

Responsibilities:
- Load and normalize catalog.json (UI-facing metadata)
- Remain OPTIONAL and additive to games.json
- Never affect ranking, routing, eligibility, or learning

games.json:
- Authoritative source of game identity and status

catalog.json:
- Optional presentation metadata (icons, links, localized overrides)
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple


# Default path relative to this file
_DEFAULT_CATALOG_JSON_PATH = Path(__file__).with_name("catalog.json")


class CatalogConfigError(RuntimeError):
    """Raised when catalog.json is present but malformed."""


# ------------------------------------------------------------
# Internal normalization
# ------------------------------------------------------------

def _normalize_catalog_node(node: Any) -> Dict[str, Dict[str, Any]]:
    """
    Normalize catalog data into a dict keyed by game_id.

    Supports:
    - dict[game_id -> metadata]
    - list[{ game_id, ... }]
    """
    if node is None:
        return {}

    if isinstance(node, dict):
        return {
            str(k): v for k, v in node.items()
            if isinstance(v, dict)
        }

    if isinstance(node, list):
        out: Dict[str, Dict[str, Any]] = {}
        for item in node:
            if not isinstance(item, dict):
                continue
            gid = item.get("game_id")
            if gid:
                out[str(gid)] = dict(item)
        return out

    raise CatalogConfigError("catalog node must be a dict or list")


# ------------------------------------------------------------
# Public loaders
# ------------------------------------------------------------

def load_catalog_config(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """
    Load and normalize catalog.json.

    Raises CatalogConfigError if present but malformed.
    """
    p = Path(path) if path else _DEFAULT_CATALOG_JSON_PATH
    if not p.exists():
        raise CatalogConfigError("catalog.json not found")

    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CatalogConfigError("catalog.json must be an object")

    catalog = _normalize_catalog_node(raw.get("catalog"))
    return {"catalog": catalog}


def load_catalog_config_optional(path: Optional[str | Path] = None) -> Dict[str, Any]:
    """
    Load catalog.json if present, otherwise return empty catalog.
    """
    try:
        return load_catalog_config(path)
    except Exception:
        return {"catalog": {}}


# ------------------------------------------------------------
# Convenience helpers (presentation‑only)
# ------------------------------------------------------------

def get_all_catalog_entries(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    cfg = config or load_catalog_config_optional()
    return cfg.get("catalog", {})


def get_catalog_entry(
    game_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return get_all_catalog_entries(config).get(str(game_id), {})


def get_display_overrides(
    game_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = get_catalog_entry(game_id, config)
    return entry.get("display", {}) if isinstance(entry, dict) else {}


# ------------------------------------------------------------
# Optional cross‑checks (CI / tooling only)
# ------------------------------------------------------------

def diff_games_vs_catalog(
    *,
    games: Dict[str, Dict[str, Any]],
    catalog: Dict[str, Dict[str, Any]],
) -> Tuple[Set[str], Set[str]]:
    """
    Return:
      (missing_in_catalog, extra_in_catalog)
    """
    game_ids = set(games.keys())
    catalog_ids = set(catalog.keys())
    return game_ids - catalog_ids, catalog_ids - game_ids


__all__ = [
    "CatalogConfigError",
    "load_catalog_config",
    "load_catalog_config_optional",
    "get_all_catalog_entries",
    "get_catalog_entry",
    "get_display_overrides",
    "diff_games_vs_catalog",
]
