import json
from pathlib import Path

SCHEMA_FILE = "PHASE_4_EVENT_LOG.schema.json"


def test_event_logging_schema_exists():
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / SCHEMA_FILE

    assert schema_path.exists(), f"{SCHEMA_FILE} does not exist"


def test_event_logging_schema_is_valid_json():
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / SCHEMA_FILE

    with open(schema_path, encoding="utf-8") as f:
        try:
            obj = json.load(f)
        except Exception as e:
            raise AssertionError(f"Invalid JSON schema: {e}")

    assert isinstance(obj, dict), "Schema root must be an object"