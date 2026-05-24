"""
CI Test — Capability Fixtures Load & Validate
"""

from __future__ import annotations

import json
from pathlib import Path


def _find_fixture_root() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "fixtures" / "game_capability",
        Path(__file__).resolve().parents[2] / "fixtures" / "game_capability",
        Path(__file__).resolve().parents[3] / "fixtures" / "game_capability",
    ]
    for p in candidates:
        if p.exists():
            return p

    raise AssertionError(f"No capability fixture directory found: {candidates}")


def test_game_capability_fixtures_load_and_validate():
    root = _find_fixture_root()

    cap_map = {}

    for path in root.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        game_id = data.get("game_id")
        assert game_id, f"{path.name} missing game_id"
        cap_map[game_id] = data

    assert cap_map, f"No capability fixtures found in {root}"