from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from .registry import GameRegistry, GameInfo


def load_games_registry(path: str | Path = "games.json") -> GameRegistry:
    """
    Load Phase 7 game registry from games.json.

    CI requirements:
    - Must not crash on valid JSON
    - Must ignore malformed entries safely
    - Must return a GameRegistry object
    """

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"games.json not found at: {p}")

    raw = json.loads(p.read_text(encoding="utf-8"))

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
    Convenience loader for tests / CI (dict input).
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