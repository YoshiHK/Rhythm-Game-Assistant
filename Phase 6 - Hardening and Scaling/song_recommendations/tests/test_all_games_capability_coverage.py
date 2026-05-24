"""
CI Test — All Games Capability Coverage (Phase 6)

Purpose:
- Ensure every capability fixture resolves
"""

from __future__ import annotations

import json
from pathlib import Path

from song_recommendations.game_capability_resolver import resolve_game_capability


def test_all_fixture_capabilities_resolve():
    # ✅ correct path (relative to this file)
    root = Path(__file__).resolve().parent / "fixtures" / "game_capability"

    # ✅ ensure dir exists
    assert root.exists(), f"Fixture directory not found: {root}"

    fixtures = sorted(root.glob("*.json"))
    assert fixtures, f"No capability fixtures found in {root}"

    cap_map = {}

    for path in fixtures:
        data = json.loads(path.read_text(encoding="utf-8"))
        game_id = data.get("game_id")
        assert game_id, f"{path.name} missing game_id"
        cap_map[game_id] = data

    for gid in cap_map:
        resolved = resolve_game_capability(gid, capabilities=cap_map)
        assert resolved.game_id == gid