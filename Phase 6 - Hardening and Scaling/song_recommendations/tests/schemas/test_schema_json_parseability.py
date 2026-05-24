from __future__ import annotations

import json
from pathlib import Path


def test_all_song_recommendation_schemas_are_parseable():
    schema_dir = Path(__file__).parent.parent.parent / "schemas"

    assert schema_dir.exists(), f"Schema directory not found: {schema_dir}"

    files = sorted(schema_dir.glob("*.json"))
    assert files, "No schema files found"

    errors = []

    for path in files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{path.name}: {e}")

    assert not errors, "Invalid JSON:\n" + "\n".join(errors)