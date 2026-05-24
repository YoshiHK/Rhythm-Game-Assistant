"""
CI Test — Song Recommendation Schema JSON Parseability

Purpose:
Ensure all JSON schema files are valid JSON (no syntax errors).
"""

from __future__ import annotations

import json
from pathlib import Path


def test_all_song_recommendation_schemas_are_parseable():
    schema_dir = Path(__file__).parent.parent.parent / "schemas"

    assert schema_dir.exists(), f"Schema directory not found: {schema_dir}"

    files = list(schema_dir.glob("*.json"))
    assert files, "No schema files found"

    for path in files:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            raise AssertionError(f"Invalid JSON in {path.name}: {e}")

        assert isinstance(obj, dict), f"{path.name} root must be an object"