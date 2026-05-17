"""
Phase 4 CI — Fixture-Based Determinism Regression (Design-LPhase 4 CI — Fixture-Based Determinism Regression (Design-Locked)
- Enforce deterministic behavior for identical inputs

This is the ONLY Phase 4 CI test allowed to execute runtime code.

Non-goals:
- Does NOT evaluate personalization quality
- Does NOT judge ranking, narrative, or model correctness
- Does NOT enforce explainability or safety invariants
  (those are covered by dedicated Phase 4 CI checks)

If this test fails, it indicates an architectural regression,
not a product-quality issue.
"""

from __future__ import annotations

import pytest
import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Fields that are allowed to vary across runs and MUST be scrubbed
VOLATILE_KEY_TOKENS = (
    "timestamp",
    "time",
    "datetime",
    "decision_timestamp",
    "event_timestamp",
)


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def scrub(obj: Any):
    """
    Remove volatile, non-deterministic fields from output.
    This is an intentional governance decision, not a workaround.
    """
    if isinstance(obj, dict):
        return {
            k: scrub(v)
            for k, v in obj.items()
            if not any(tok in k.lower() for tok in VOLATILE_KEY_TOKENS)
        }
    if isinstance(obj, list):
        return [scrub(x) for x in obj]
    return obj


def stable_hash(obj: Any) -> str:
    """
    Compute a canonical, deterministic hash of the output payload.
    """
    try:
        text = json.dumps(
            obj,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
    except Exception as e:
        fail(f"Output is not JSON-serializable: {e}")

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_fixture(fixture: dict):
    """
    Execute Phase 4 runtime once for a single fixture input.
    """
    try:
        from phase4_personalization_runtime import run_phase4_personalization
    except Exception as e:
        fail(f"Unable to import Phase 4 runtime: {e}")

    return run_phase4_personalization(**fixture)


def main() -> int:
    inputs = sorted(FIXTURES_DIR.glob("fixture_*_input.json"))
    if not inputs:
        fail("No Phase 4 fixture inputs found")

    for inp in inputs:
        try:
            data = json.loads(inp.read_text(encoding="utf-8"))
        except Exception as e:
            fail(f"Invalid fixture JSON ({inp.name}): {e}")

        out1 = scrub(run_fixture(data))
        out2 = scrub(run_fixture(data))

        if not isinstance(out1, dict) or not isinstance(out2, dict):
            fail(f"Phase 4 output must be a dict (fixture={inp.name})")

        h1 = stable_hash(out1)
        h2 = stable_hash(out2)

        if h1 != h2:
            fail(
                "Non-deterministic Phase 4 output detected "
                f"(fixture={inp.name}, hash1={h1}, hash2={h2})"
            )

    print("CI PASS: Phase 4 fixture determinism regression verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
    
@pytest.mark.phase4_determinism
def test_fixture_determinism_regression():
    """
    Pytest wrapper for fixture-based determinism regression.

    Ensures:
    - identical inputs produce identical outputs (after scrub)
    - Phase 4 runtime is deterministic

    This is the ONLY pytest test that executes Phase 4 runtime at scale.
    """

    inputs = sorted(FIXTURES_DIR.glob("fixture_*_input.json"))

    assert inputs, "No Phase 4 fixture inputs found"

    for path in inputs:
        with open(path, encoding="utf-8") as f:
            fixture = json.load(f)

        # ✅ Run twice (determinism check)
        out1 = run_fixture(fixture)
        out2 = run_fixture(fixture)

        # ✅ scrub volatile fields
        s1 = scrub(out1)
        s2 = scrub(out2)

        h1 = stable_hash(s1)
        h2 = stable_hash(s2)

        assert h1 == h2, f"Determinism violated for fixture: {path.name}"
