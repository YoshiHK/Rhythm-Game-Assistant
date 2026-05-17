import json
from pathlib import Path

def _phase4_root() -> Path:
    # tests live under Phase 4 - Personalization/ci/tests
    return Path(__file__).resolve().parents[2]

def test_event_logging_schema_exists():
    schema_path = _phase4_root() / "schemas" / "event_log.schema.json"
    assert schema_path.exists(), f"event_log.schema.json does not exist at {schema_path}"

def test_event_logging_schema_is_valid_json():
    schema_path = _phase4_root() / "schemas" / "event_log.schema.json"
    with open(schema_path, encoding="utf-8") as f:
        obj = json.load(f)
    assert isinstance(obj, dict), "Schema root must be an object"
