from __future__ import annotations
"""
[game_router.py](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s40ac7976b989459ca1582b508e6c13dc&EntityRepresentationId=f3ef6382-2d29-4c90-b860-5e966f043fee)

Phase 3 control-plane helper:
- Load games.json (single source of truth)
- Build extension allowlist for file_scan
- Build routing helpers (extension -> candidate games, game_id aliases)

This module is routing/control-plane only.
It does NOT parse charts and does NOT select adapters at runtime by heuristics.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import json


DEFAULT_CONFIG_PATH = Path("src/rhythm_ingestion/config/games.json")


@dataclass(frozen=True)
class GamesRouting:
    # All extensions permitted for scanning (union across enabled adapter games)
    allowed_extensions: Tuple[str, ...]

    # ext -> list of game_ids that claim it (can be >1, e.g. .json)
    ext_to_game_ids: Dict[str, List[str]]

    # alias(lower) -> canonical game_id (handles _meta.game_id_aliases)
    game_id_aliases: Dict[str, str]


def load_games_config(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_game_id_aliases(cfg: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}

    # map canonical game ids to themselves
    for g in cfg.get("games", []) or []:
        gid = str(g.get("game_id", "")).strip()
        if gid:
            out[gid.casefold()] = gid

    meta = cfg.get("_meta") or {}
    for entry in meta.get("game_id_aliases", []) or []:
        canonical = str(entry.get("canonical", "")).strip()
        if not canonical:
            continue
        out[canonical.casefold()] = canonical
        for a in entry.get("aliases", []) or []:
            alias = str(a).strip()
            if alias:
                out[alias.casefold()] = canonical

    return out


def build_extensions_union(cfg: Dict[str, Any]) -> Tuple[Tuple[str, ...], Dict[str, List[str]]]:
    """
    Only include games where capabilities.adapter == "enabled".
    For each game, take supported_extensions.adapter.
    """
    allowed: Set[str] = set()
    ext_to_games: Dict[str, List[str]] = {}

    for g in cfg.get("games", []) or []:
        caps = g.get("capabilities", {}) or {}
        if caps.get("adapter") != "enabled":
            continue

        gid = str(g.get("game_id", "")).strip()
        exts = (g.get("supported_extensions", {}) or {}).get("adapter", []) or []
        for ext in exts:
            e = str(ext).strip().lower()
            if not e:
                continue
            allowed.add(e)
            ext_to_games.setdefault(e, []).append(gid)

    # deterministic ordering
    allowed_sorted = tuple(sorted(allowed, key=lambda s: (len(s), s)))
    # keep ext_to_games deterministic too
    for e in list(ext_to_games.keys()):
        ext_to_games[e] = sorted(ext_to_games[e], key=lambda s: s.casefold())

    return allowed_sorted, ext_to_games


def build_routing(config_path: Path = DEFAULT_CONFIG_PATH) -> GamesRouting:
    cfg = load_games_config(config_path)
    aliases = build_game_id_aliases(cfg)
    allowed_exts, ext_to_games = build_extensions_union(cfg)
    return GamesRouting(
        allowed_extensions=allowed_exts,
        ext_to_game_ids=ext_to_games,
        game_id_aliases=aliases,
    )


def detect_game_by_extension(path: Path, routing: GamesRouting) -> Tuple[Optional[str], str]:
    """
    Deterministic extension-based hint:
    - Uses longest suffix match first (supports multi-ext like .maidata.txt)
    - If unique game for that extension -> returns game_id
    - If ambiguous -> returns None + reason
    """
    name = path.name.lower()
    for ext in sorted(routing.ext_to_game_ids.keys(), key=len, reverse=True):
        if name.endswith(ext):
            games = routing.ext_to_game_ids[ext]
            if len(games) == 1:
                return games[0], f"ext:{ext}"
            return None, f"ambiguous_ext:{ext}:{games}"
    return None, "no_ext_match"


__all__ = [
    "GamesRouting",
    "DEFAULT_CONFIG_PATH",
    "load_games_config",
    "build_routing",
    "detect_game_by_extension",
]