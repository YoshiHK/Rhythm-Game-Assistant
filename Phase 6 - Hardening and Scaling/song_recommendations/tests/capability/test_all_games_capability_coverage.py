"""
CI Test — All Games Capability Coverage (Phase 6)

Purpose:
- Ensure every capability fixture in fixtures/game_capability is loadable
  and resolvable by the resolver.
- This is a coverage test over the fixture set (not a correctness test).
"""

from __future__ import annotations

import json
from pathlib import Path

from song_recommendations.game_capability_resolver import resolve_game_capability


def test_all_fixture_capabilities_resolve():
   root = Path(__file__).resolve().parent / "fixtures" / "game_capability"
    fixtures = sorted(root.glob("*.json"))
    assert fixtures, f"No capability fixtures found in {root}"

    cap_map = {}
    for p in fixtures:
        data = json.loads(p.read_text(encoding="utf-8"))
        gid = data.get("game_id")
        assert gid, f"{p.name} missing game_id"
        cap_map[gid] = data

    for gid in cap_map:
        resolved = resolve_game_capability(gid, capabilities=cap_map)
        assert resolved.game_id == gid