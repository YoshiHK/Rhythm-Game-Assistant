"""Phase 4 CI: Personalization Decision Schema

Purpose
-------
Ensures Phase 4 decision-making is governed by an explicit interface/contract.

This test validates the presence of the decision interface document and (if present)
any related schema files.

This is a structural/policy check only.
"""

import json
from pathlib import Path


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    # Contract docs/schemas expected for Phase 4
    required_docs = [
        'PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md',
        'PHASE_4_SAFE_ADJUSTMENT_INTERFACE.md',
    ]

    for d in required_docs:
        if not Path(d).exists():
            fail(f"Missing required Phase 4 contract doc: {d}")

    # Optional: validate provenance schema JSON is parseable if present
    prov = Path('PHASE_4_PROVENANCE.schema.json')
    if prov.exists():
        try:
            obj = json.loads(prov.read_text(encoding='utf-8'))
            if not isinstance(obj, dict):
                fail('PHASE_4_PROVENANCE.schema.json root must be an object')
        except Exception as e:
            fail(f"Failed to parse PHASE_4_PROVENANCE.schema.json: {e}")

    print('CI PASS: Phase 4 decision interface + safe adjustment interface present')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
