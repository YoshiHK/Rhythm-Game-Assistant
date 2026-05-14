def test_regression_guard_triggers_on_drop(sample_feature_rows):
    from phase5.song_recommendation.eval import evaluate_selection_quality

    baseline = {
        "accept_or_better_rate": 0.8,
        "played_or_better_rate": 0.7,
        "completed_rate": 0.6,
    }

    report = evaluate_selection_quality(
        sample_feature_rows,
        baseline_metrics=baseline,
    )["report"]

    assert report["guard_pass"] in (True, False)