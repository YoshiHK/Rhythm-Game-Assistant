"""
CI Test — Game Capability Ladder Invariants (Phase 6)

Purpose
-------
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
        from .song_recommendations.game_capability_resolver import resolve_game_capability
        return resolve_game_capability
    except Exception:
        from .game_capability_resolver import resolve_game_capability
        return resolve_game_capability


def _load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise AssertionError(f"JSON root must be an object: {path}")
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

    # Paths: adjust if your repo layout differs
    repo_root = Path(__file__).parents[3]
    registry_path = repo_root / "phase6" / "song_recommendation" / "capability_registry.json"

    assert registry_path.exists(), "capability_registry.json must exist"

    registry = _load_json(registry_path)

    # Validate all game entries in registry (skip _meta keys)
    for game_id, cfg in registry.items():
        if str(game_id).startswith("_"):
            continue

        assert isinstance(cfg, dict), f"{game_id} capability entry must be an object"

        tiers = cfg.get("difficulty_tiers")
        ladder = cfg.get("completion_ladder")

        _assert_string_list(f"{game_id}.difficulty_tiers", tiers)
        _assert_string_list(f"{game_id}.completion_ladder", ladder)

        # Ladder must have at least 2 levels (otherwise “progression” is undefined)
        assert len(ladder) >= 2, f"{game_id}.completion_ladder must have length >= 2"

        # Optional alias objects must be dict[str,str] if present
        for k in ("tier_aliases", "completion_aliases"):
            if k in cfg:
                assert isinstance(cfg[k], dict), f"{game_id}.{k} must be an object"
                for ak, av in cfg[k].items():
                    assert isinstance(ak, str) and ak.strip(), f"{game_id}.{k} keys must be non-empty strings"
                    assert isinstance(av, str) and av.strip(), f"{game_id}.{k} values must be non-empty strings"

        # Also ensure resolver can parse the registry entry
        # (resolve_game_capability expects registry keyed by game_id -> dict config)
        cap = resolve_game_capability(game_id, capabilities=registry)
        assert cap.game_id == game_id
        assert cap.difficulty_tiers
        assert cap.completion_ladder