from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from .registry import GameRegistry, GameInfo


def _resolve_games_json(path: str | Path) -> Path:
    """
    Resolve games.json location in a CI-safe way.

    Resolution order:
    1. Explicit path
    2. Phase 7 directory
    3. Repo root
    """

    p = Path(path)

    # ✅ 1. direct path
    if p.exists():
        return p

    # ✅ 2. Phase 7 directory
    phase7_dir = Path(__file__).resolve().parent.parent
    candidate = phase7_dir / "games.json"
    if candidate.exists():
        return candidate

    # ✅ 3. repo root (one level above Phase 7)
    repo_root = phase7_dir.parent
    candidate = repo_root / "games.json"
    if candidate.exists():
        return candidate

    raise FileNotFoundError(f"games.json not found (searched: {path})")


def load_games_registry(path: str | Path = "games.json") -> GameRegistry:
    """
    Load Phase 7 game registry from games.json.

    CI requirements:
    - Must not crash on valid JSON
    - Must ignore malformed entries
    - Must work across local + CI environments
    """

    p = _resolve_games_json(path)

    raw: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))

    games: List[GameInfo] = []

    for obj in raw.get("games", []):
        if not isinstance(obj, dict):
            continue

        game_id = obj.get("game_id")
        display_name = obj.get("display_name")
        status = obj.get("overall_status")

        if not game_id or not display_name or not status:
            continue

        games.append(
            GameInfo(
                game_id=str(game_id),
                display_name=str(display_name),
                status=str(status),
            )
        )

    return GameRegistry(games=games)


def load_games_registry_from_dict(raw: Dict[str, Any]) -> GameRegistry:
    """
    CI helper: load registry from dict without file access.
    """

    games: List[GameInfo] = []

    for obj in raw.get("games", []):
        if not isinstance(obj, dict):
            continue

        game_id = obj.get("game_id")
        display_name = obj.get("display_name")
        status = obj.get("overall_status")

        if not game_id or not display_name or not status:
            continue

        games.append(
            GameInfo(
                game_id=str(game_id),
                display_name=str(display_name),
                status=str(status),
            )
        )

    return GameRegistry(games=games)


__all__ = [
    "load_games_registry",
    "load_games_registry_from_dict",
]