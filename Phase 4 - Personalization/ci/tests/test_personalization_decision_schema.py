from pathlib import Path


def test_phase4_decision_schema_exists():
    repo_root = Path(__file__).resolve().parents[2]

    schema = repo_root / "Phase 4 - Personalization" / "decision_schema.json"

    assert schema.exists(), "Decision schema file is missing"


def test_phase4_decision_schema_min_keys():
    repo_root = Path(__file__).resolve().parents[2]

    schema = repo_root / "Phase 4 - Personalization" / "decision_schema.json"

    import json

    with open(schema, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "Schema root must be object"

    for key in ("decision_source", "safe_adjustment"):
        assert key in data, f"Missing required key: {key}"