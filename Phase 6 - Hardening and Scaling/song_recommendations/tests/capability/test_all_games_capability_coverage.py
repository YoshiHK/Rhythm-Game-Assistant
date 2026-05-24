"""
CI Test — All Games Capability Coverage (Phase 6)

Purpose:
- Ensure every VALID capability fixture resolves
"""

from __future__ import annotations

import json
from pathlib import Path

from song_recommendations.game_capability_resolver import resolve_game_capability


def _find_fixture_root() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "fixtures" / "game_capability",
        Path(__file__).resolve().parents[2] / "fixtures" / "game_capability",
        Path(__file__).resolve().parents[3] / "fixtures" / "game_capability",
    ]

    for p in candidates:
        if p.exists():
            return p

    raise AssertionError("No capability fixture directory found")


def _is_valid_capability(data: dict) -> bool:
    """Only pass tests for valid fixtures"""
    if not isinstance(data.get("difficulty_tiers"), list):
        return False
    if not isinstance(data.get("completion_ladder"), list):
        return False
    return True


def test_all_fixture_capabilities_resolve():
    root = _find_fixture_root()

    fixtures = sorted(root.glob("*.json"))
    assert fixtures, f"No capability fixtures found in {root}"

    cap_map = {}

    for path in fixtures:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not _is_valid_capability(data):
            # ✅ skip invalid fixture (e.g. broken_game)
            continue

        game_id = data.get("game_id")
        assert game_id, f"{path.name} missing game_id"
        cap_map[game_id] = data

    assert cap_map, "No valid capability fixtures found"

    for gid in cap_map:
        resolved = resolve_game_capability(gid, capabilities=cap_map)
        assert resolved.game_id == gid