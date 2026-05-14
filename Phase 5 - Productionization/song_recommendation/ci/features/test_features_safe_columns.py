def test_features_only_emit_safe_columns(sample_aggregated_rows):
    from phase5.song_recommendation.features import build_selection_feature_rows

    out = build_selection_feature_rows(sample_aggregated_rows)
    row = out["rows"][0]

    forbidden = {"tips", "taxonomy", "severity", "narrative"}
    assert forbidden.isdisjoint(set(row.keys()))