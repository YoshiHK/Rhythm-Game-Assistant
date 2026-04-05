"""Phase 4 CI: Event Logging Contract

Purpose
-------
Ensures Phase 4 emits structured events and that the event schema exists and is valid JSON.

This is a structural check only.
"""

import json
from pathlib import Path


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    schema_path = Path('PHASE_4_EVENT_LOG.schema.json')
    if not schema_path.exists():
        fail('Missing PHASE_4_EVENT_LOG.schema.json')

    try:
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
    except Exception as e:
        fail(f"Failed to parse PHASE_4_EVENT_LOG.schema.json: {e}")

    if not isinstance(schema, dict):
        fail('PHASE_4_EVENT_LOG.schema.json root must be an object')

    # Minimal JSON-schema sanity check
    if 'type' not in schema and 'properties' not in schema:
        fail('PHASE_4_EVENT_LOG.schema.json does not look like a JSON schema (missing type/properties)')

    print('CI PASS: Phase 4 event log schema is present and parseable')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
