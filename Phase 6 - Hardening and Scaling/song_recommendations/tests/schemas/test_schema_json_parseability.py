"""
CI Test — Song Recommendation Schema JSON Parseability

Purpose
-------
Ensure all JSON schema files under phase6/song_recommendation/schemas
are valid JSON and loadable.

This test is intentionally minimal:
- It does NOT validate schema semantics
- It only guards against broken JSON that would crash tooling/CI/runtime
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_all_song_recommendation_schemas_are_parseable():
    # Adjust path if your repo layout differs
    repo_root = Path(__file__).parents[3]
    schemas_dir = repo_root / "phase6" / "song_recommendation" / "schemas"

    assert schemas_dir.exists(), "schemas directory must exist"
    assert schemas_dir.is_dir(), "schemas path must be a directory"

    schema_files = sorted(schemas_dir.glob("*.schema.json"))
    assert schema_files, "No *.schema.json files found under schemas directory"

    for path in schema_files:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise AssertionError(f"Schema file is not valid JSON: {path}\n{e}") from e

        assert isinstance(obj, dict), f"Schema root must be an object: {path}"
        # Optional sanity check: schema id/title presence
        assert "$schema" in obj, f"$schema missing in {path}"
        assert "$id" in obj, f"$id missing in {path}"