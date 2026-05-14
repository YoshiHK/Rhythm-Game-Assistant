def test_evaluation_metrics_present(sample_feature_rows):
    from phase5.song_recommendation.eval import evaluate_selection_quality

    report = evaluate_selection_quality(sample_feature_rows)["report"]
    metrics = report["metrics"]

    for key in [
        "accept_or_better_rate",
        "played_or_better_rate",
        "completed_rate",
    ]:
        assert key in metrics