import pytest

@pytest.mark.deterministic
def test_training_is_deterministic_and_order_independent(sample_feature_rows):
    from phase5.song_recommendation.training import train_song_selector_params

    out1 = train_song_selector_params(sample_feature_rows)
    out2 = train_song_selector_params(sample_feature_rows)
    out3 = train_song_selector_params(list(reversed(sample_feature_rows)))

    assert out1 == out2
    assert out1 == out3