"""
CI Test — Capability Ladder Invariants
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

    raise AssertionError("No capability fixture directory found")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_capability_registry_ladder_invariants():
    root = _find_fixture_root()

    cap_map = {}

    for p in root.glob("*.json"):
        data = _load_json(p)
        gid = data.get("game_id")
        assert gid, f"{p.name} missing game_id"

        ladder = data.get("completion_ladder")
        assert isinstance(ladder, list), f"{gid} ladder must be list"
        assert len(ladder) >= 1, f"{gid} ladder must not be empty"

        cap_map[gid] = data

    assert cap_map, "No capability fixtures found"
