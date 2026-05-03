#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""games_loader.py

Loader utilities for config/games.json used by the Unified Ingestion Manager (UMI), Phase 3.

Responsibilities
----------------
- Load and parse games.json (v3)
- Normalize schema differences (games list vs dict)
- Resolve game_id aliases (data-driven)
- Provide safe, structured access to game capability metadata
- Provide UI badge mapping helpers (wiring-only)
- Remain completely decoupled from adapters, validators, and gameplay logic

Notes
-----
- This module is wiring/config only (Phase 3). It does not modify any completed phases.
- games.json v3 uses:
  - _meta.status_priority
  - games: [ {game_id, display_name, supported_extensions, capabilities, overall_status}, ... ]
- Some older configs may still provide games as a dict; we normalize both forms.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable

_DEFAULT_GAMES_JSON_PATH = Path(__file__).with_name('games.json')


class GamesConfigError(RuntimeError):
    """Raised when games.json is missing or malformed."""


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _status_priority(cfg: Dict[str, Any]) -> List[str]:
    meta = cfg.get('_meta') if isinstance(cfg.get('_meta'), dict) else {}
    pr = meta.get('status_priority')
    if isinstance(pr, list) and all(isinstance(x, str) for x in pr):
        return [str(x).strip().lower() for x in pr]
    return ['rulebook', 'anchor', 'enabled', 'disabled', 'future']


def _normalize_status_for_priority(s: Any) -> str:
    if not isinstance(s, str):
        return ''
    v = s.strip().lower()
    # treat ready as enabled for gating
    if v == 'ready':
        return 'enabled'
    return v


def _best_status(statuses: Iterable[str], priority: List[str]) -> str:
    rank = {p: i for i, p in enumerate(priority)}
    best: Tuple[int, str] = (10**9, '')
    for s in statuses:
        ss = _normalize_status_for_priority(s)
        if not ss:
            continue
        r = rank.get(ss, 10**8)
        if r < best[0]:
            best = (r, ss)
    return best[1] or 'future'


def _compute_overall_status(game_meta: Dict[str, Any], priority: List[str]) -> str:
    # Prefer explicit overall_status
    if isinstance(game_meta.get('overall_status'), str) and game_meta.get('overall_status').strip():
        return str(game_meta['overall_status']).strip().lower()

    # Otherwise derive from capabilities values (best status wins)
    caps = game_meta.get('capabilities') if isinstance(game_meta.get('capabilities'), dict) else {}
    values: List[str] = []
    for _k, v in caps.items():
        if isinstance(v, str):
            values.append(v)
    return _best_status(values, priority)


# ----------------------------------------------------------------------
# Alias helpers (data-driven)
# ----------------------------------------------------------------------

def _load_alias_pairs(raw_cfg: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Load alias pairs (alias -> canonical) from games.json _meta.game_id_aliases.

    Supported formats:
      A) list of {canonical: str, aliases: [str,...]}
      B) dict mapping canonical -> [aliases]
    """
    meta = raw_cfg.get('_meta') if isinstance(raw_cfg.get('_meta'), dict) else {}
    node = meta.get('game_id_aliases')
    pairs: List[Tuple[str, str]] = []

    if isinstance(node, list):
        for item in node:
            if not isinstance(item, dict):
                continue
            canonical = item.get('canonical')
            aliases = item.get('aliases')
            if not isinstance(canonical, str) or not canonical.strip():
                continue
            if isinstance(aliases, list):
                for a in aliases:
                    if isinstance(a, str) and a.strip():
                        pairs.append((a.strip(), canonical.strip()))
        return pairs

    if isinstance(node, dict):
        for canonical, aliases in node.items():
            if not isinstance(canonical, str) or not canonical.strip():
                continue
            if isinstance(aliases, list):
                for a in aliases:
                    if isinstance(a, str) and a.strip():
                        pairs.append((a.strip(), canonical.strip()))
        return pairs

    return pairs


def _build_alias_map(existing_game_ids: Iterable[str], pairs: List[Tuple[str, str]]) -> Dict[str, str]:
    """Build a case-insensitive alias->canonical map limited to existing canonical ids."""
    existing = {gid.strip(): gid.strip() for gid in existing_game_ids if isinstance(gid, str) and gid.strip()}
    alias_to_key: Dict[str, str] = {}

    # Always map canonical to itself
    for gid in existing.keys():
        alias_to_key[gid.lower()] = gid

    for alias, canonical in pairs:
        c = canonical.strip()
        if c not in existing:
            continue
        a = alias.strip()
        if not a:
            continue
        alias_to_key[a.lower()] = c

    return alias_to_key


def _resolve_game_id(game_id: str, alias_to_key: Dict[str, str]) -> Optional[str]:
    if not isinstance(game_id, str) or not game_id.strip():
        return None
    return alias_to_key.get(game_id.strip().lower())


# ----------------------------------------------------------------------
# Extension merging helpers
# ----------------------------------------------------------------------

def _normalize_ext(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        x = str(x)
    if not isinstance(x, str):
        return None
    s = x.strip()
    if not s:
        return None
    if not s.startswith('.'):
        s = '.' + s
    s = s.lower()
    return None if s == '.' else s


def _extract_ext_list(node: Any) -> List[str]:
    if not isinstance(node, list):
        return []
    out: List[str] = []
    for x in node:
        nx = _normalize_ext(x)
        if nx:
            out.append(nx)
    return out


def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        if it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


def merge_supported_extensions(game_meta: Dict[str, Any]) -> Dict[str, List[str]]:
    """Return {'schema': [...], 'adapter': [...], 'merged': [...]}.

    games.json v3 shape:
      supported_extensions: {schema: [...], adapter: [...]}
    Also supports older shapes as best-effort.
    """
    schema_ext: List[str] = []
    adapter_ext: List[str] = []

    se = game_meta.get('supported_extensions')
    if isinstance(se, dict):
        schema_ext = _extract_ext_list(se.get('schema'))
        adapter_ext = _extract_ext_list(se.get('adapter'))
    else:
        # legacy fallbacks
        schema_ext = _extract_ext_list(game_meta.get('schema_extensions'))
        adapter_ext = _extract_ext_list(game_meta.get('adapter_extensions'))

    merged = _unique_preserve_order([*schema_ext, *adapter_ext])
    return {'schema': schema_ext, 'adapter': adapter_ext, 'merged': merged}


# ----------------------------------------------------------------------
# Normalization: games list -> dict
# ----------------------------------------------------------------------

def _normalize_games_node(games_node: Any) -> Dict[str, Dict[str, Any]]:
    """Normalize games node to {game_id: meta} dict."""
    if games_node is None:
        return {}

    if isinstance(games_node, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for gid, meta in games_node.items():
            if not isinstance(gid, str) or not gid.strip():
                continue
            if not isinstance(meta, dict):
                continue
            out[gid.strip()] = dict(meta)
        return out

    if isinstance(games_node, list):
        out: Dict[str, Dict[str, Any]] = {}
        for item in games_node:
            if not isinstance(item, dict):
                continue
            gid = item.get('game_id')
            if not isinstance(gid, str) or not gid.strip():
                continue
            out[gid.strip()] = dict(item)
        return out

    return {}


# ----------------------------------------------------------------------
# Public loader
# ----------------------------------------------------------------------

def load_games_config(path: Optional[str] = None) -> Dict[str, Any]:
    p = Path(path) if path is not None else _DEFAULT_GAMES_JSON_PATH
    if not p.exists():
        raise GamesConfigError(f'games.json not found: {p}')

    try:
        raw = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        raise GamesConfigError(f'games.json is malformed: {e}')

    if not isinstance(raw, dict):
        raise GamesConfigError('games.json root must be an object')

    games_dict = _normalize_games_node(raw.get('games'))

    # Compute overall_status and extension breakdown
    priority = _status_priority(raw)
    for gid, meta in games_dict.items():
        meta['overall_status'] = _compute_overall_status(meta, priority)
        meta['_extensions'] = merge_supported_extensions(meta)

    pairs = _load_alias_pairs(raw)
    alias_to_key = _build_alias_map(games_dict.keys(), pairs)

    raw['games'] = games_dict
    raw['_alias_to_game_id'] = alias_to_key
    raw['_status_priority_norm'] = priority

    # Expose alias keys (lowercase) in games dict (non-destructive)
    for alias_lower, canonical in list(alias_to_key.items()):
        if canonical in games_dict and alias_lower not in games_dict:
            games_dict[alias_lower] = games_dict[canonical]

    return raw


# ----------------------------------------------------------------------
# Convenience helpers
# ----------------------------------------------------------------------

def get_all_games(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    cfg = config or load_games_config()
    games = cfg.get('games')
    return games if isinstance(games, dict) else {}


def get_active_games(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    games = get_all_games(config)
    return {
        gid: meta
        for gid, meta in games.items()
        if str(meta.get('overall_status', '')).lower() in {'enabled', 'anchor', 'rulebook'}
    }


def get_enabled_games(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    return get_active_games(config)


def get_games_by_overall_status(status: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    target = (status or '').strip().lower()
    games = get_all_games(config)
    return {gid: meta for gid, meta in games.items() if str(meta.get('overall_status', '')).lower() == target}


def get_games_with_capability(
    capability: str,
    allowed_statuses: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return games whose capabilities[capability] is within allowed_statuses."""
    cap = (capability or '').strip()
    if not cap:
        return {}
    allowed = allowed_statuses or ['enabled', 'anchor', 'rulebook', 'ready']
    allowed_set = {_normalize_status_for_priority(a) for a in allowed if isinstance(a, str)}

    games = get_all_games(config)
    out: Dict[str, Dict[str, Any]] = {}
    for gid, meta in games.items():
        caps = meta.get('capabilities')
        if not isinstance(caps, dict):
            continue
        v = caps.get(cap)
        if isinstance(v, str) and _normalize_status_for_priority(v) in allowed_set:
            out[gid] = meta
    return out


def get_games_supporting_tips(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """Heuristic: games that are overall active and have adapter/validator/schema enabled.

    Aligns with the app definition: all enabled games are allowed to enter the tips pipeline;
    runtime may degrade depending on chart structure.
    """
    games = get_active_games(config)
    out: Dict[str, Dict[str, Any]] = {}
    for gid, meta in games.items():
        caps = meta.get('capabilities')
        if not isinstance(caps, dict):
            continue
        a = _normalize_status_for_priority(caps.get('adapter'))
        v = _normalize_status_for_priority(caps.get('validator'))
        s = _normalize_status_for_priority(caps.get('schema'))
        if a in {'enabled', 'anchor', 'rulebook'} and v in {'enabled', 'anchor', 'rulebook'} and s in {'enabled', 'anchor', 'rulebook'}:
            out[gid] = meta
    return out


def get_game_config(game_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config or load_games_config()
    games = cfg.get('games')
    if not isinstance(games, dict):
        raise GamesConfigError('Malformed games config: games must be a dict after normalization')

    alias_map = cfg.get('_alias_to_game_id') if isinstance(cfg.get('_alias_to_game_id'), dict) else {}
    resolved = _resolve_game_id(game_id, alias_map)
    key = resolved or (game_id.strip() if isinstance(game_id, str) else '')

    if not key or key not in games:
        raise GamesConfigError(f'Unknown game_id: {game_id}')

    meta = games[key]
    if isinstance(meta, dict) and '_extensions' not in meta:
        meta['_extensions'] = merge_supported_extensions(meta)
    return meta


def get_supported_extensions(
    game_id: str,
    config: Optional[Dict[str, Any]] = None,
    *,
    include_schema: bool = True,
    include_adapter: bool = True,
) -> List[str]:
    game = get_game_config(game_id, config)
    ex = game.get('_extensions')
    if isinstance(ex, dict):
        schema = list(ex.get('schema', [])) if include_schema else []
        adapter = list(ex.get('adapter', [])) if include_adapter else []
        return _unique_preserve_order([*schema, *adapter])

    br = merge_supported_extensions(game)
    schema = br['schema'] if include_schema else []
    adapter = br['adapter'] if include_adapter else []
    return _unique_preserve_order([*schema, *adapter])


def get_supported_extensions_breakdown(game_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
    game = get_game_config(game_id, config)
    ex = game.get('_extensions')
    if isinstance(ex, dict):
        schema = list(ex.get('schema', []))
        adapter = list(ex.get('adapter', []))
        merged = _unique_preserve_order([*schema, *adapter])
        return {'schema': schema, 'adapter': adapter, 'merged': merged}

    br = merge_supported_extensions(game)
    return {'schema': br['schema'], 'adapter': br['adapter'], 'merged': br['merged']}

__all__ = [
    'GamesConfigError',
    'load_games_config',
    'get_all_games',
    'get_active_games',
    'get_enabled_games',
    'get_games_by_overall_status',
    'get_games_with_capability',
    'get_games_supporting_tips',
    'get_game_config',
    'get_supported_extensions',
    'get_supported_extensions_breakdown',
    'merge_supported_extensions',
    # UI badge mapping exports
    'STATUS_BADGES',
    'CAPABILITY_BADGES',
    'get_status_badge',
    'get_capability_badge',
    'get_game_badges',
]
