import pytest

def test_aggregation_rejects_semantic_fields():
    from phase5.song_recommendation.aggregation import aggregate_song_feedback_events

    bad_event = {
        "event_type": "phase6.song_feedback",
        "player_id": "p1",
        "game_id": "g1",
        "recommendation_set_id": "s1",
        "song_id": "songA",
        "action": "accept",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "tips": "do jackhammers faster",  # ❌ forbidden
    }

    out = aggregate_song_feedback_events([bad_event])
    assert out["rows"] == []