"""
Phase 4 CI — Personalization Decision Schema (Design-Locked)

Purpose:
- Ensure Phase 4 decision-making is governed by explicit, versioned contracts
- Prevent silent removal of decision or safe-adjustment interfaces

This is a STRUCTURAL / POLICY test.
It does not validate runtime behavior or decision semantics.
"""

import json
from pathlib import Path
import sys


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    # Required contract documents for Phase 4
    required_docs = [
        "PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md",
        "PHASE_4_SAFE_ADJUSTMENT_INTERFACE.md",
    ]

    for doc in required_docs:
        path = repo_root / doc
        if not path.exists():
            fail(f"Missing required Phase 4 contract document: {doc}")

    # Optional: provenance schema must be parseable if present
    prov_schema = repo_root / "PHASE_4_PROVENANCE.schema.json"
    if prov_schema.exists():
        try:
            obj = json.loads(prov_schema.read_text(encoding="utf-8"))
        except Exception as e:
            fail(f"Failed to parse PHASE_4_PROVENANCE.schema.json: {e}")

        if not isinstance(obj, dict):
            fail("PHASE_4_PROVENANCE.schema.json root must be a JSON object")

    print("CI PASS: Phase 4 decision + safe adjustment contracts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())