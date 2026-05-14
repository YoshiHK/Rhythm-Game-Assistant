import pytest

@pytest.mark.deterministic
def test_features_are_deterministic_and_order_independent(sample_aggregated_rows):
    from phase5.song_recommendation.features import build_selection_feature_rows

    out1 = build_selection_feature_rows(sample_aggregated_rows)
    out2 = build_selection_feature_rows(sample_aggregated_rows)
    out3 = build_selection_feature_rows(list(reversed(sample_aggregated_rows)))

    assert out1 == out2
    assert out1 == out3

    # Sanity: must emit rows + summary
    assert "rows" in out1
    assert "summary" in out1