def test_orchestrator_runs_end_to_end(tmp_path, sample_feedback_events):
    from phase5.song_recommendation.utils import run_song_rec_learning_pipeline

    result = run_song_rec_learning_pipeline(
        events=sample_feedback_events,
        artifact_root_dir=tmp_path,
    )

    assert result["status"] in ("OK", "GUARD_FAIL")
    assert "selector_params" in result["paths"]