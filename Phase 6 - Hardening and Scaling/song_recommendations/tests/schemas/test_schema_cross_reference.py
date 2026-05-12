"""
CI Test — Schema Cross Reference Consistency (Phase 6)

Purpose
-------
Ensure Song Recommendation schemas remain structurally consistent
with each other.

This test verifies that:
- Response schema references recommendation item schema
- Recommendation item schema references rationale schema
- Response schema references persistence plan schema

This prevents silent schema drift across files.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load_schema(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"Schema root must be object: {path}"
    return obj


def test_song_recommendation_schema_cross_references():
    repo_root = Path(__file__).parents[3]
    schemas_dir = repo_root / "phase6" / "song_recommendation" / "schemas"

    response_schema = _load_schema(schemas_dir / "song_recommendation_response.schema.json")
    item_schema = _load_schema(schemas_dir / "recommendation_item.schema.json")
    rationale_schema = _load_schema(schemas_dir / "rationale.schema.json")
    persistence_schema = _load_schema(schemas_dir / "persistence_plan.schema.json")

    # --- Response → RecommendationItem ---
    response_defs = response_schema.get("$defs", {})
    assert "RecommendationItem" in response_defs, \
        "Response schema must define RecommendationItem in $defs"

    # --- Response → PersistencePlan ---
    assert "PersistencePlan" in response_defs, \
        "Response schema must define PersistencePlan in $defs"

    # --- RecommendationItem → Rationale ---
    item_props = item_schema.get("properties", {})
    assert "rationale" in item_props, \
        "RecommendationItem must include rationale field"

    rationale_ref = item_props["rationale"]
    assert "$ref" in rationale_ref or rationale_ref.get("type") == "object", \
        "RecommendationItem.rationale must reference or inline rationale schema"

    # --- Rationale must enforce explainability ---
    rationale_required = set(rationale_schema.get("required", []))
    assert {"summary", "why"} <= rationale_required, \
        "Rationale schema must require summary and why"

    # --- PersistencePlan must enforce save semantics ---
    persistence_required = set(persistence_schema.get("required", []))
    assert {"did_save", "created_count", "delete_ids", "delete_count"} <= persistence_required, \
        "PersistencePlan schema missing required save fields"
