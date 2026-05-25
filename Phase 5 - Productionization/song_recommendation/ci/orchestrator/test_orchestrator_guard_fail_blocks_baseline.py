def test_guard_fail_does_not_update_baseline(tmp_path, sample_feedback_events):
    from phase5.song_recommendation.utils import (
        run_song_rec_learning_pipeline,
        OrchestratorConfig,
    )

    cfg = OrchestratorConfig(
        update_baseline_snapshot=True,
        strict=False,
    )

    result = run_song_rec_learning_pipeline(
        events=sample_feedback_events,
        artifact_root_dir=tmp_path,
        config=cfg,
    )

    if result["status"] == "GUARD_FAIL":
        assert result["paths"]["baseline_metrics"] is None