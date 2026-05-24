"""
Song Recommendation CI Test — Request Normalizer Contract

Ensures request normalization is multi-game safe and schema-enforcing.
"""

from __future__ import annotations

import pytest

from song_recommendations.request_normalizer import (
    normalize_song_recommendation_request,
    ContractError,
)


def test_minimal_valid_request_normalizes():
    req = normalize_song_recommendation_request(
        {
            "game_id": "proseka",
            "mode": "songs",
            "action": "refresh",
            "submission": {
                "difficulty_progress": {
                    "tiers": [
                        {"tier_id": "expert", "counts": {"clear": 1, "fc": 0, "ap": 0}}
                    ]
                }
            },
        }
    )

    assert req.game_id == "proseka"
    assert req.mode == "songs"
    assert req.action == "refresh"
    assert req.submission.tiers[0]["tier_id"] == "expert"
    assert isinstance(req.submission.tiers[0]["counts"], dict)


def test_invalid_mode_rejected():
    with pytest.raises(ContractError):
        normalize_song_recommendation_request(
            {
                "game_id": "proseka",
                "mode": "games",  # ❌ invalid
                "submission": {
                    "difficulty_progress": {
                        "tiers": [{"tier_id": "x", "counts": {"y": 1}}]
                    }
                },
            }
        )