def test_training_does_not_import_phase6():
    import inspect
    from phase5.song_recommendation.training import train_song_selector_params

    src = inspect.getsource(train_song_selector_params)
    assert "phase6" not in src