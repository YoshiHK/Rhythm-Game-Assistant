"""
CI Test — Game Capability Ladder Invariants (Phase 6)

### Purpose

Lock mechanical invariants of multi-game capability configs so that
song recommendation routing remains multi-game safe and deterministic.
This test does NOT judge whether a ladder is "correct" for a game.
It only enforces structural invariants that must always hold.

Invariants:
- difficulty_tiers: non-empty list of unique non-empty strings
- completion_ladder: length >= 2, unique non-empty strings
- No whitespace-only entries
- No duplicates
- Every required (enabled/anchor) game in games.json has a registry entry
(coverage test is separate; this test validates invariants for registry contents)
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest


def _imports():
    try:
        from .song_recommendations.game_capability_resolver import (
            resolve_game_capability,
        )
        return resolve_game_capability
    except Exception:
        from .game_capability_resolver import resolve_game_capability
        return resolve_game_capability


def _load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise AssertionError("JSON root must be an object")
    return obj


def _assert_string_list(name: str, xs):
    assert isinstance(xs, list), f"{name} must be a list"
    assert len(xs) > 0, f"{name} must be non-empty"
    for i, v in enumerate(xs):
        assert isinstance(v, str), f"{name}[{i}] must be a string"
        assert v.strip(), f"{name}[{i}] must not be empty/whitespace"
    # Deterministic uniqueness
    assert len(set(xs)) == len(xs), f"{name} must not contain duplicates"


def test_capability_registry_ladder_invariants():
    resolve_game_capability = _imports()

    fixtures_dir = (
        Path(__file__).parent.parent / "fixtures" / "game_capability"
    )

    for path in fixtures_dir.glob("*.json"):
        cfg = _load_json(path)

        game_id = cfg.get("game_id")
        assert isinstance(game_id, str) and game_id.strip(), "game_id must be a non-empty string"

        difficulty_tiers = cfg.get("difficulty_tiers")
        completion_ladder = cfg.get("completion_ladder")

        _assert_string_list("difficulty_tiers", difficulty_tiers)
        _assert_string_list("completion_ladder", completion_ladder)
        assert len(completion_ladder) >= 2, "completion_ladder must have length >= 2"

        # ------------------------------------------------------------------
        # Game-specific hard invariants (Phase 6 safety rails)
        # ------------------------------------------------------------------

        if game_id == "ユメステ":
            # World Dai Star has a fixed 5-tier ladder:
            # NORMAL → HARD → EXTRA → STELLA → OLIVIER
            assert difficulty_tiers == [
                "normal",
                "hard",
                "extra",
                "stella",
                "olivier",
            ], "ユメステ difficulty ladder must be exactly 5 fixed tiers in canonical order"