def test_outcome_priority_completed_wins():
    from phase5.song_recommendation.aggregation import aggregate_song_feedback_events

    events = [
        {"event_type":"phase6.song_feedback","player_id":"p","game_id":"g",
         "recommendation_set_id":"r","song_id":"s","action":"accept",
         "timestamp_utc":"2026-01-01T00:00:00Z"},
        {"event_type":"phase6.song_feedback","player_id":"p","game_id":"g",
         "recommendation_set_id":"r","song_id":"s","action":"completed",
         "timestamp_utc":"2026-01-01T01:00:00Z"},
    ]

    rows = aggregate_song_feedback_events(events)["rows"]
    assert rows[0]["final_outcome"] == "completed"