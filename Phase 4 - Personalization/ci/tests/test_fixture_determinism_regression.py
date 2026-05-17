"""
Phase 4 CI — Fixture-Based Determinism Regression (pytest-native)

Purpose:
- Enforce deterministic behavior for identical inputs (after scrubbing volatile fields)
- This is a regression / architecture test, NOT a quality test.

Markers:
- phase4_determinism
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict

import pytest

# ✅ fixtures live in Phase 4 - Personalization/ci/fixtures
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

# Fields allowed to vary across runs and must be scrubbed
VOLATILE_KEY_TOKENS = (
    "timestamp",
    "time",
    "datetime",
    "decision_timestamp",
    "event_timestamp",
)


def scrub(obj: Any):
    """Remove volatile, non-deterministic fields from output (governance decision)."""
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
    """Compute a canonical, deterministic hash of a JSON-serializable object."""
    text = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_fixture(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute Phase 4 runtime once for a single fixture input.
    NOTE: This should import the runtime wrapper aligned with your routing skeleton.
    """
    try:
        from runtime.runtime_wrapper import run_phase4_personalization
    except Exception as e:
        raise AssertionError(f"Unable to import Phase 4 runtime: {e}")

    for k in ("canonical_payload", "canonical_row", "selected_elements", "difficulty"):
        assert k in fixture, f"Fixture missing required key '{k}'"

    out = run_phase4_personalization(
        canonical_payload=fixture["canonical_payload"],
        canonical_row=fixture["canonical_row"],
        elements_skeleton=fixture["selected_elements"],   # Phase 4 uses elements_skeleton
        difficulty=fixture["difficulty"],
        engine_mode=str(fixture.get("engine_mode", "deterministic")),
        locale=fixture.get("locale"),
        player_context=fixture.get("player_context"),
        feature_flags=fixture.get("feature_flags"),
        opt_in=fixture.get("opt_in"),
    )
    assert isinstance(out, dict), "Phase 4 runtime output must be a dict"
    return out

@pytest.mark.phase4_determinism
def test_fixture_determinism_regression():
    inputs = sorted(FIXTURES_DIR.glob("fixture_*_input.json"))
    assert inputs, f"No Phase 4 fixture inputs found in {FIXTURES_DIR}"

    for path in inputs:
        fixture = json.loads(path.read_text(encoding="utf-8"))

        # Run twice for determinism
        out1 = run_fixture(fixture)
        out2 = run_fixture(fixture)

        h1 = stable_hash(scrub(out1))
        h2 = stable_hash(scrub(out2))

        assert h1 == h2, f"Determinism violated for fixture: {path.name}"