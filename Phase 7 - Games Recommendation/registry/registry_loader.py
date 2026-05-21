from pathlib import Path
import json

# Paths
pkg_path = Path('rhythm_recommendation/phase7')
pkg_path.mkdir(parents=True, exist_ok=True)

# Load games.json if exists in cwd
games_json_path = Path('games.json')
raw = None
if games_json_path.exists():
    raw = json.loads(games_json_path.read_text(encoding='utf-8'))

# Create a Phase 7 registry module that directly supports the games.json schema.
registry_code = from __future__ import annotations

Phase 7 — Game Registry (games recommendation)

This module is the Phase 7 read-only adapter over the authoritative <File>games.json</File>
registry used by ingestion.

Design constraints (Phase 7 SPEC):
- Downstream-only: Phase 7 consumes registry metadata but does not modify it.
- No semantic reinterpretation: status values are respected as-is.
- Wiring-flexible: the registry source can be swapped (file path, dict, injected loader)
  without touching completed phases.

The <File>games.json</File> format in this repo contains:
{
  "_meta": {...},
  "games": [
     {"game_id": "proseka", "display_name": "Project SEKAI", "status": "enabled"},
     ...
  ]
}

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence
import json
from pathlib import Path


# ----------------------------
# Data contracts
# ----------------------------

@dataclass(frozen=True)
class GameInfo:
    Canonical game metadata for Phase 7 routing and filtering.

    game_id: str
    display_name: str
    status: str  # expected values: enabled | ingestion_only | future | disabled (others allowed)

    # Optional fields (may be absent in games.json today; reserved for Phase 7 growth)
    platforms: Optional[List[str]] = None
    locales: Optional[List[str]] = None
    tags: Optional[List[str]] = None


@dataclass(frozen=True)
class RegistryMeta:
    description: str = ''
    notes: str = ''


class GameRegistry:
    """Read-only registry for Phase 7.

    This class provides:
    - loading from the authoritative games.json schema
    - stable filtering helpers for Phase 7 routing

    It MUST NOT make product decisions; it only exposes metadata.
    """

    def __init__(self, *, games: Sequence[GameInfo], meta: Optional[RegistryMeta] = None):
        self._meta = meta or RegistryMeta()
        self._games: Dict[str, GameInfo] = {g.game_id: g for g in games if g and g.game_id}

    # ---- Accessors ----
    @property
    def meta(self) -> RegistryMeta:
        return self._meta

    def all(self) -> Dict[str, GameInfo]:
        return dict(self._games)

    def get(self, game_id: str) -> Optional[GameInfo]:
        return self._games.get(str(game_id))

    def list_game_ids(self) -> List[str]:
        return sorted(self._games.keys())

    # ---- Filtering (routing-safe) ----
    def game_ids_by_status(self, *statuses: str) -> List[str]:
        allowed = {str(s) for s in statuses if s is not None}
        return sorted([gid for gid, info in self._games.items() if info.status in allowed])

    def recommendable_game_ids(self, *, strict: bool = True) -> List[str]:
        """Return game IDs that Phase 7 is allowed to recommend.

        strict=True  -> only status == 'enabled'
        strict=False -> allow 'enabled' and 'ingestion_only' (for internal/testing)

        NOTE: Phase 7 ranker/explainer may apply additional constraints (platform/locale),
        but this method does not. It is registry-only.
        """
        if strict:
            return self.game_ids_by_status('enabled')
        return self.game_ids_by_status('enabled', 'ingestion_only')

    def filter_by_platform(self, game_ids: Iterable[str], *, platform: Optional[str]) -> List[str]:
        """Filter candidate game IDs by platform if platform metadata exists.

        If a game has no platform metadata, it is kept (non-blocking default).
        """
        if not platform:
            return list(game_ids)
        p = str(platform).lower()
        out: List[str] = []
        for gid in game_ids:
            info = self.get(gid)
            if info is None:
                continue
            if not info.platforms:
                out.append(gid)
                continue
            plats = [str(x).lower() for x in info.platforms]
            if p in plats:
                out.append(gid)
        return out

    def filter_by_locale(self, game_ids: Iterable[str], *, locale: Optional[str]) -> List[str]:
        """Filter candidate game IDs by locale if locale metadata exists.

        If a game has no locales metadata, it is kept (non-blocking default).
        """
        if not locale:
            return list(game_ids)
        loc = str(locale).lower()
        out: List[str] = []
        for gid in game_ids:
            info = self.get(gid)
            if info is None:
                continue
            if not info.locales:
                out.append(gid)
                continue
            locs = [str(x).lower() for x in info.locales]
            if loc in locs:
                out.append(gid)
        return out


# ----------------------------
# Loaders
# ----------------------------

def _parse_meta(raw: Any) -> RegistryMeta:
    if not isinstance(raw, dict):
        return RegistryMeta()
    return RegistryMeta(
        description=str(raw.get('description') or ''),
        notes=str(raw.get('notes') or ''),
    )


def _parse_game(obj: Any) -> Optional[GameInfo]:
    if not isinstance(obj, dict):
        return None
    game_id = obj.get('game_id')
    display_name = obj.get('display_name')
    status = obj.get('status')
    if not game_id or not display_name or not status:
        return None

    platforms = obj.get('platforms')
    locales = obj.get('locales')
    tags = obj.get('tags')

    return GameInfo(
        game_id=str(game_id),
        display_name=str(display_name),
        status=str(status),
        platforms=list(platforms) if isinstance(platforms, list) else None,
        locales=list(locales) if isinstance(locales, list) else None,
        tags=list(tags) if isinstance(tags, list) else None,
    )


def load_games_registry_from_dict(raw: Dict[str, Any]) -> GameRegistry:
    """Load a <File>games.json</File>-shaped dict into a GameRegistry."""
    meta = _parse_meta(raw.get('_meta'))
    games_raw = raw.get('games')
    games: List[GameInfo] = []
    if isinstance(games_raw, list):
        for g in games_raw:
            parsed = _parse_game(g)
            if parsed is not None:
                games.append(parsed)
    return GameRegistry(games=games, meta=meta)


def load_games_registry(path: str | Path = 'games.json') -> GameRegistry:
    """Load registry from a JSON file path (default: games.json)."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError('games registry JSON must be an object')
    return load_games_registry_from_dict(raw)
'''

(pkg_path / 'registry.py').write_text(registry_code, encoding='utf-8')

# Also update build.py to use the new loader signature if present
build_path = pkg_path / 'build.py'
if build_path.exists():
    text = build_path.read_text(encoding='utf-8')
    # Keep existing content but add convenient bridge to load_games_registry
    if 'load_games_registry' not in text:
        addition = "\n\n# Convenience: wire Phase 7 registry to the authoritative games.json schema\nfrom .registry import load_games_registry, load_games_registry_from_dict\n"
        build_path.write_text(text + addition, encoding='utf-8')

print('Updated registry/registry.py to load games.json schema')
print('Detected games.json entries:', len(raw.get('games', [])) if isinstance(raw, dict) else 'N/A')
