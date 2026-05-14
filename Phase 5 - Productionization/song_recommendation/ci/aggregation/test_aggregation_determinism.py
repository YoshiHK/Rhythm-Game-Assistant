def test_aggregation_is_deterministic(sample_feedback_events):
    from phase5.song_recommendation.aggregation import aggregate_song_feedback_events

    out1 = aggregate_song_feedback_events(sample_feedback_events)
    out2 = aggregate_song_feedback_events(sample_feedback_events)

    assert out1 == out2
