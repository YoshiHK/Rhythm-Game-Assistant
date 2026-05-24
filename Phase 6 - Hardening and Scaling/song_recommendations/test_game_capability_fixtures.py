"""
CI Test — Game Capability Fixtures Validity

Ensures ALL fixture JSON files:
- are valid JSON
- can be resolved by game_capability_resolver
"""

from __future__ import annotations

import json
from pathlib import Path


def _imports():
    try:
        from .song_recommendations.game_capability_resolver import resolve_game_capability
        return resolve_game_capability
    except Exception:
        from .game_capability_resolver import resolve_game_capability
        return resolve_game_capability


def test_game_capability_fixtures_load_and_validate():
    resolve_game_capability = _imports()

    root = Path(__file__).parent / "fixtures" / "game_capability"

    cap_map = {}

    for path in root.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))

        game_id = data.get("game_id")
        assert game_id, f"{path.name} missing game_id"

        cap_map[game_id] = data

    for game_id in cap_map:
        resolved = resolve_game_capability(game_id, capabilities=cap_map)
        assert resolved.game_id == game_id