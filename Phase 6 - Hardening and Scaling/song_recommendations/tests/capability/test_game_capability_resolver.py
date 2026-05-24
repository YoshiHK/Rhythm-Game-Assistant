"""
Song Recommendation CI Test — Game Capability Resolver

Ensures game capability config resolves tier/ladder ordering deterministically.
"""

from __future__ import annotations

import pytest

from song_recommendations.game_capability_resolver import (
    resolve_game_capability,
    canonicalize_tier_id,
    canonicalize_completion_id,
    CapabilityError,
)


def test_proseka_defaults_resolve():
    cap = resolve_game_capability("proseka")
    assert cap.difficulty_tiers[:1] == ["expert"]
    assert cap.completion_ladder[-1] in {"ap", "AP", "ap".lower()}
    assert canonicalize_tier_id(cap, "Expert") == "expert"
    assert canonicalize_completion_id(cap, "AllPerfect") == "ap"


def test_missing_game_capability_fails():
    with pytest.raises(CapabilityError):
        resolve_game_capability("nonexistent_game_id_zzz")