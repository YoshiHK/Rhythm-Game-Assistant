from __future__ import annotations

import json
from pathlib import Path


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_song_recommendation_schema_cross_references():
    schema_dir = Path(__file__).parent.parent.parent / "schemas"

    assert schema_dir.exists(), f"Schema directory not found: {schema_dir}"

    response_path = schema_dir / "song_recommendation_response.schema.json"
    item_path = schema_dir / "recommendation_item.schema.json"
    rationale_path = schema_dir / "rationale.schema.json"
    persistence_path = schema_dir / "persistence_plan.schema.json"

    # ensure all exist
    assert response_path.exists(), "Missing response schema"
    assert item_path.exists(), "Missing recommendation_item schema"
    assert rationale_path.exists(), "Missing rationale schema"
    assert persistence_path.exists(), "Missing persistence schema"

    response = _load_schema(response_path)
    item = _load_schema(item_path)

    response_str = json.dumps(response).lower()
    item_str = json.dumps(item).lower()

    # Response must reference item schema
    assert "recommendation_item" in response_str, "response must reference recommendation_item schema"

    # Response must reference persistence
    assert "persistence" in response_str or "persistence_plan" in response_str

    # Item must reference rationale
    assert "rationale" in item_str, "item must reference rationale schema"