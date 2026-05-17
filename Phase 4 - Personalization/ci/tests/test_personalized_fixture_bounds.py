"""
Phase 4 CI — Bounded-Safety Assertions (Personalized Fixtures)

Design-Locked — aligned with Phase 4 routing skeleton.

Enforces (structural / invariants only):
- No element creation/deletion (permutation)
- No semantic field mutation on elements_view
- Allowed adjustment keys only
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest

# ✅ fixtures live under ci/fixtures (routing skeleton)
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

IMMUTABLE_ELEMENT_FIELDS = (
    "severity_label",
    "score",
    "training_items",
    "matched_tags",
    "guidance",
)

ALLOWED_ADJUSTMENT_KEYS = {
    "element_ordering",
    "ranking_weights",
    "narrative_template_id",
    "variant_id",
}


def load_json(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"Fixture root must be an object: {path}"
    return obj


def is_personalized_fixture(fx: Dict[str, Any]) -> bool:
    return str(fx.get("engine_mode", "")).strip().lower() == "personalized"


def index_by_element_id(elements: List[Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for el in elements:
        if isinstance(el, dict):
            eid = el.get("element_id")
            if isinstance(eid, str) and eid:
                out[eid] = el
    return out


def assert_permutation(input_ids: List[str], output_ids: List[str]) -> None:
    assert sorted(input_ids) == sorted(output_ids), (
        "elements_view is not a permutation of input elements. "
        f"Missing={sorted(set(input_ids)-set(output_ids))} "
        f"Extra={sorted(set(output_ids)-set(input_ids))}"
    )


def run_phase4(fixture: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from runtime.runtime_wrapper import run_phase4_personalization
    except Exception as e:
        raise AssertionError(f"Unable to import Phase 4 runtime: {e}")

    for k in ("canonical_payload", "canonical_row", "selected_elements", "difficulty"):
        assert k in fixture, f"Fixture missing required key '{k}'"

    # NOTE: runtime signature uses elements_skeleton (routing skeleton runtime spine)
    out = run_phase4_personalization(
        canonical_payload=fixture["canonical_payload"],
        canonical_row=fixture["canonical_row"],
        elements_skeleton=fixture["selected_elements"],
        difficulty=fixture["difficulty"],
        engine_mode="personalized",
        locale=fixture.get("locale"),
        feature_flags=fixture.get("feature_flags"),
        opt_in=fixture.get("opt_in"),
        player_context=fixture.get("player_context"),
    )
    assert isinstance(out, dict), "Phase 4 runtime output must be a dict"
    return out


def assert_no_semantic_mutation(fixture: Dict[str, Any], out: Dict[str, Any]) -> None:
    inp_elements = fixture["selected_elements"]
    out_elements = out["elements_view"]

    inp_idx = index_by_element_id(inp_elements)
    out_idx = index_by_element_id(out_elements)

    assert inp_idx, "No element_id found in fixture selected_elements"
    assert out_idx, "No element_id found in output elements_view"

    assert_permutation(list(inp_idx.keys()), list(out_idx.keys()))

    for eid in inp_idx:
        for field in IMMUTABLE_ELEMENT_FIELDS:
            assert inp_idx[eid].get(field) == out_idx[eid].get(field), f"{field} changed for {eid}"

    applied = out.get("applied_adjustments") or {}
    assert isinstance(applied, dict), "applied_adjustments must be an object"
    extra = sorted(set(applied.keys()) - ALLOWED_ADJUSTMENT_KEYS)
    assert not extra, f"applied_adjustments contains disallowed keys: {extra}"

@pytest.mark.phase4_policy
def test_personalized_fixture_bounds():
    inputs = sorted(FIXTURES_DIR.glob("fixture_*_input.json"))
    assert inputs, f"No fixtures found in {FIXTURES_DIR}"

    ran = 0
    for p in inputs:
        fx = load_json(p)
        if not is_personalized_fixture(fx):
            continue

        out = run_phase4(fx)
        assert_no_semantic_mutation(fx, out)
        ran += 1

    assert ran > 0, "No personalized fixtures executed (expected at least one)"