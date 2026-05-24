"""
CI Test — Game Capability Ladder Invariants (Phase 6)

Purpose:
Lock mechanical invariants of multi-game capability configs so that
song recommendation routing remains multi-game safe and deterministic.

Invariants:
- difficulty_tiers: non-empty list of unique non-empty strings
- completion_ladder: length >= 2, unique non-empty strings
- No whitespace-only entries
- No duplicates
"""

from __future__ import annotations

import json
from pathlib import Path

from song_recommendations.game_capability_resolver import resolve_game_capability


def _load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"JSON root must be an object: {path.name}"
    return obj


def _assert_string_list(name: str, xs):
    assert isinstance(xs, list), f"{name} must be a list"
    assert len(xs) > 0, f"{name} must be non-empty"
    for i, v in enumerate(xs):
        assert isinstance(v, str), f"{name}[{i}] must be a string"
        assert v.strip(), f"{name}[{i}] must not be empty/whitespace"
    assert len(set(xs)) == len(xs), f"{name} must not contain duplicates"


def test_capability_registry_ladder_invariants():
    root = Path(__file__).parents[4] / "song_recommendations" / "tests" / "capability" / "fixtures" / "game_capability"
    cap_map = {}

    for p in root.glob("*.json"):
        data = _load_json(p)
        gid = data.get("game_id")
        assert gid, f"{p.name} missing game_id"
        cap_map[gid] = data

    assert cap_map, "No capability fixtures found"

    # Validate invariants on each fixture by resolving into GameCapability
    for gid in cap_map:
        cap = resolve_game_capability(gid, capabilities=cap_map)
        _assert_string_list("difficulty_tiers", cap.difficulty_tiers)
        _assert_string_list("completion_ladder", cap.completion_ladder)
        assert len(cap.completion_ladder) >= 2, "completion_ladder must have length >= 2"