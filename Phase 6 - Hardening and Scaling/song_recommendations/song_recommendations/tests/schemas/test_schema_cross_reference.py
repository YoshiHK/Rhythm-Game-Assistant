"""
CI Test — Schema Cross Reference Consistency (Phase 6)

Purpose:
Ensure schema files reference each other correctly.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_schema(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"Schema root must be object: {path.name}"
    return obj


def test_song_recommendation_schema_cross_references():
    schema_dir = Path(__file__).parent.parent.parent / "schemas"

    assert schema_dir.exists(), f"Schema directory not found: {schema_dir}"

    # Load schemas
    response = _load_schema(schema_dir / "song_recommendation_response.schema.json")
    item = _load_schema(schema_dir / "recommendation_item.schema.json")
    rationale = _load_schema(schema_dir / "rationale.schema.json")
    persistence = _load_schema(schema_dir / "persistence_plan.schema.json")

    # ✅ Simple cross reference checks (non-strict but effective)

    response_str = json.dumps(response)
    item_str = json.dumps(item)

    # Response references item + persistence
    assert "recommendation_item" in response_str.lower()
    assert "persistence" in response_str.lower()

    # Item references rationale
    assert "rationale" in item_str.lower()