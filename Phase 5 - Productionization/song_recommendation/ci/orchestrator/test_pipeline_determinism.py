import pytest

@pytest.mark.deterministic
def test_song_rec_learning_pipeline_is_deterministic(tmp_path, sample_feedback_events):
    from phase5.song_recommendation.utils import run_song_rec_learning_pipeline

    out1 = run_song_rec_learning_pipeline(
        events=sample_feedback_events,
        artifact_root_dir=tmp_path / "run1",
    )

    out2 = run_song_rec_learning_pipeline(
        events=sample_feedback_events,
        artifact_root_dir=tmp_path / "run2",
    )

    assert out1["status"] == out2["status"]
    assert out1["summary"] == out2["summary"]

    for key in ["selector_params", "training_report", "evaluation_report"]:
        with open(out1["paths"][key], "r", encoding="utf-8") as f1, \
             open(out2["paths"][key], "r", encoding="utf-8") as f2:
            assert f1.read() == f2.read()


@pytest.mark.deterministic
def test_song_rec_learning_pipeline_order_independent(tmp_path, sample_feedback_events):
    from phase5.song_recommendation.utils import run_song_rec_learning_pipeline

    normal = run_song_rec_learning_pipeline(
        events=sample_feedback_events,
        artifact_root_dir=tmp_path / "normal",
    )

    reversed_run = run_song_rec_learning_pipeline(
        events=list(reversed(sample_feedback_events)),
        artifact_root_dir=tmp_path / "reversed",
    )

    assert normal["summary"] == reversed_run["summary"]

    for key in ["selector_params", "training_report", "evaluation_report"]:
        with open(normal["paths"][key], "r", encoding="utf-8") as f1, \
             open(reversed_run["paths"][key], "r", encoding="utf-8") as f2:
            assert f1.read() == f2.read()
           