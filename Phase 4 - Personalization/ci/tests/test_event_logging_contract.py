"""
Phase 4 CI — Event Logging Contract (Design-Locked)

Purpose:
- Ensure Phase 4 event logging schema exists
- Ensure schema is valid JSON and structurally sane

This is a CONTRACT EXISTENCE test.
"""

import json
from pathlib import Path
import sys


SCHEMA_FILE = "PHASE_4_EVENT_LOG.schema.json"


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = repo_root / SCHEMA_FILE

    if not schema_path.exists():
        fail(f"Missing Phase 4 event log schema: {SCHEMA_FILE}")

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Failed to parse {SCHEMA_FILE}: {e}")

    if not isinstance(schema, dict):
        fail(f"{SCHEMA_FILE} root must be a JSON object")

    if "properties" not in schema and "type" not in schema:
        fail(f"{SCHEMA_FILE} does not appear to be a valid JSON schema")

    print("CI PASS: Phase 4 event logging contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())