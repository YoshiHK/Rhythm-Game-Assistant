def test_training_outputs_static_params(sample_feature_rows):
    from phase5.song_recommendation.training import train_song_selector_params

    out = train_song_selector_params(sample_feature_rows)
    params = out["params"]

    assert "selector_params" in params
    assert isinstance(params["selector_params"]["widen_steps"], list)