import pytest

@pytest.mark.deterministic
def test_evaluation_is_deterministic(sample_feature_rows):
    from phase5.song_recommendation.eval import evaluate_selection_quality

    out1 = evaluate_selection_quality(sample_feature_rows)
    out2 = evaluate_selection_quality(sample_feature_rows)

    assert out1 == out2


def test_evaluation_order_independent(sample_feature_rows):
    from phase5.song_recommendation.eval import evaluate_selection_quality

    out1 = evaluate_selection_quality(sample_feature_rows)
    out2 = evaluate_selection_quality(list(reversed(sample_feature_rows)))

    assert out1 == out2


def test_evaluation_metrics_are_present(sample_feature_rows):
    from phase5.song_recommendation.eval import evaluate_selection_quality

    report = evaluate_selection_quality(sample_feature_rows)["report"]
    metrics = report["metrics"]

    for key in [
        "accept_or_better_rate",
        "played_or_better_rate",
        "completed_rate",
    ]:
        assert key in metrics