"""
Song Recommendation CI Test — Coordinator Integration (Phase 6)

Purpose
-------
End-to-end integration test for the Phase 6 song recommendation wiring:

normalize request
→ resolve game capability (difficulty tiers + completion ladder)
→ catalog loader (in-memory artifacts)
→ catalog selector (deterministic)
→ coordinator generates 3-in-a-group (AP/FC/Clear logical types)
→ persistence plan (save/rotation)
→ response shaping (stable set_id + JSON serializable)

Invariants enforced:
- Deterministic output for identical inputs
- Exclusions respected (song_id-based)
- Multi-game safe: no hardcoded Proseka-only assumptions in request schema
"""

from __future__ import annotations

import json
import pytest


def _imports():
    """
    Support both:
    - package layout: phase6.song_recommendation.*
    - flat layout: modules in current PYTHONPATH
    """
    try:
        from phase6.song_recommendation.request_normalizer import normalize_song_recommendation_request
        from phase6.song_recommendation.game_capability_resolver import resolve_game_capability
        from phase6.song_recommendation.catalog_loader import load_catalog_from_artifacts
        from phase6.song_recommendation.catalog_selector import make_catalog_selector
        from phase6.song_recommendation.song_rec_coordinator import generate_recommendation_items
        from phase6.song_recommendation.persistence_policy import compute_persistence_plan
        from phase6.song_recommendation.response_shaper import shape_song_recommendation_response
        return (
            normalize_song_recommendation_request,
            resolve_game_capability,
            load_catalog_from_artifacts,
            make_catalog_selector,
            generate_recommendation_items,
            compute_persistence_plan,
            shape_song_recommendation_response,
        )
    except Exception:
        from request_normalizer import normalize_song_recommendation_request
        from game_capability_resolver import resolve_game_capability
        from catalog_loader import load_catalog_from_artifacts
        from catalog_selector import make_catalog_selector
        from song_rec_coordinator import generate_recommendation_items
        from persistence_policy import compute_persistence_plan
        from response_shaper import shape_song_recommendation_response
        return (
            normalize_song_recommendation_request,
            resolve_game_capability,
            load_catalog_from_artifacts,
            make_catalog_selector,
            generate_recommendation_items,
            compute_persistence_plan,
            shape_song_recommendation_response,
        )


def test_song_rec_integration_is_deterministic_and_respects_exclusions():
    (
        normalize_song_recommendation_request,
        resolve_game_capability,
        load_catalog_from_artifacts,
        make_catalog_selector,
        generate_recommendation_items,
        compute_persistence_plan,
        shape_song_recommendation_response,
    ) = _imports()

    # ----------------------------
    # Build request (Proseka profile, but schema is multi-game safe)
    # ----------------------------
    # This tier distribution yields:
    # total = 30 + 12 + 4 = 46
    # frac = (0*30 + 0.5*12 + 1.0*4) / 46 = 10/46 ≈ 0.217
    # AP target ≈ 11, FC target ≈ 34, Clear target ≈ 47
    payload = {
        "game_id": "proseka",
        "mode": "songs",
        "locale": "en-US",
        "max_items": 3,
        "action": "save",
        "player_id_hash": "p123",
        "submission": {
            "difficulty_progress": {
                "tiers": [
                    {"tier_id": "expert", "counts": {"clear": 30, "fc": 12, "ap": 4}},
                    {"tier_id": "master", "counts": {"clear": 0, "fc": 0, "ap": 0}},
                ]
            }
        },
        # Exclude the best AP candidate deterministically (S11A is lexicographically smallest)
        "recent_recommendations": [
            {"song_id": "S11A", "bookmarked": False, "created_at": "2026-01-01T00:00:00Z", "record_id": "R1"}
        ],
        "client": {"source": "pytest", "page": "generate"},
    }

    req = normalize_song_recommendation_request(payload)
    cap = resolve_game_capability(req.game_id)

    # ----------------------------
    # Build in-memory catalog artifacts
    # ----------------------------
    songs_artifact = {
        "songs": [
            {"song_id": "S11A", "name": "Song 11A", "producer_id": "P1"},
            {"song_id": "S11B", "name": "Song 11B", "producer_id": "P1"},
            {"song_id": "S34A", "name": "Song 34A", "producer_id": "P2"},
            {"song_id": "S47A", "name": "Song 47A", "producer_id": "P3"},
        ]
    }
    producers_artifact = {
        "producers": [
            {"producer_id": "P1", "name": "Producer 1", "avg_difficulty": 11},
            {"producer_id": "P2", "name": "Producer 2", "avg_difficulty": 34},
            {"producer_id": "P3", "name": "Producer 3", "avg_difficulty": 47},
        ]
    }
    difficulty_artifact = {
        "difficulty": [
            {"song_id": "S11A", "tier_id": "expert", "level": 11, "producer_id": "P1"},
            {"song_id": "S11B", "tier_id": "expert", "level": 11, "producer_id": "P1"},
            {"song_id": "S34A", "tier_id": "expert", "level": 34, "producer_id": "P2"},
            {"song_id": "S47A", "tier_id": "expert", "level": 47, "producer_id": "P3"},
        ]
    }

    catalog = load_catalog_from_artifacts(
        game_id=req.game_id,
        songs_artifact=songs_artifact,
        producers_artifact=producers_artifact,
        difficulty_artifact=difficulty_artifact,
    )

    selector = make_catalog_selector(catalog)

    # ----------------------------
    # Generate items -> persistence plan -> response
    # ----------------------------
    items1, diag1 = generate_recommendation_items(req, cap, selector=selector)
    plan1 = compute_persistence_plan(req, items=items1, max_history=10)
    resp1 = shape_song_recommendation_response(req, items=items1, persistence=plan1, diagnostics=diag1)

    # Determinism: run again with identical inputs
    items2, diag2 = generate_recommendation_items(req, cap, selector=selector)
    plan2 = compute_persistence_plan(req, items=items2, max_history=10)
    resp2 = shape_song_recommendation_response(req, items=items2, persistence=plan2, diagnostics=diag2)

    assert resp1 == resp2, "Full response must be deterministic for identical inputs"

    # Basic response contract
    assert resp1["mode"] == "songs"
    assert resp1["status"] == "OK"
    assert "recommendation_set" in resp1
    assert isinstance(resp1["recommendation_set"]["set_id"], str)

    # Expect up to 3 items; in this fixture it should be exactly 3.
    items = resp1["recommendation_set"]["items"]
    assert len(items) == 3

    # Must contain the three logical types (order not strictly required)
    types = {it["recommendation_type"] for it in items}
    assert types == {"AP", "FC", "Clear"}

    # Exclusion must be respected: S11A excluded, so AP (target≈11) must pick S11B
    ap_item = next(it for it in items if it["recommendation_type"] == "AP")
    assert ap_item["song_id"] == "S11B"

    # JSON serializable guarantee (CI-friendly)
    json.dumps(resp1, ensure_ascii=False)