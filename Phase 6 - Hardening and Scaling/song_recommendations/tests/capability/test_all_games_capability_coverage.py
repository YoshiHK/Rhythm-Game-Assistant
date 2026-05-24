"""
CI Test — All Games Capability Coverage (Phase 6)

Purpose:
- Ensure every capability fixture resolves
"""

from __future__ import annotations

import json
from pathlib import Path

from song_recommendations.game_capability_resolver import resolve_game_capability


def _find_fixture_root() -> Path:
    candidates = [
        # preferred: alongside this test
        Path(__file__).resolve().parent / "fixtures" / "game_capability",

        # alternative layouts (repo-level)
        Path(__file__).resolve().parents[2] / "fixtures" / "game_capability",
        Path(__file__).resolve().parents[3] / "fixtures" / "game_capability",
    ]

    for p in candidates:
        if p.exists():
            return p

    raise AssertionError(f"No capability fixture directory found. Checked:\n" + "\n".join(map(str, candidates)))


def test_all_fixture_capabilities_resolve():
    root = _find_fixture_root()

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
