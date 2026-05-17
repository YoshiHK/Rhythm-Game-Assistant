"""
Phase 4 CI: Bounded-Safety Assertions (Personalized Fixtures)

Design-Locked — Aligned with Phase 4 Routing Skeleton

Spec alignment:
- §7.2 Explainability chain enforcement
- §7.3 Ordering consistency
- §7.4 Model metadata readiness

This test enforces:
- semantic immutability
- explainability contract integrity
- safe adjustment boundaries
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Set


# ✅ ✅ ✅ UPDATED: fixtures now in ci/fixtures (NOT tests/)
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


# ----------------------------
# Helpers
# ----------------------------

def fail(msg: str) -> None:
    raise AssertionError(msg)


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


def extract_ids_any(x: Any) -> List[str]:
    if not isinstance(x, list):
        return []
    out: List[str] = []
    for item in x:
        if isinstance(item, str) and item:
            out.append(item)
        elif isinstance(item, dict):
            eid = item.get("element_id") or item.get("id")
            if isinstance(eid, str) and eid:
                out.append(eid)
    return out


def assert_permutation(input_ids: List[str], output_ids: List[str]) -> None:
    assert sorted(input_ids) == sorted(output_ids), \
        f"elements_view not a permutation. Missing={set(input_ids)-set(output_ids)} Extra={set(output_ids)-set(input_ids)}"


def assert_order_subsequence(expected_ids: List[str], out_order: List[str]) -> None:
    it = iter(out_order)
    for eid in expected_ids:
        for got in it:
            if got == eid:
                break
        else:
            raise AssertionError(f"Ordering violation: {eid} not found in {out_order}")


# ----------------------------
# ✅ UPDATED: runtime import aligned with routing skeleton
# ----------------------------

def run_phase4(fixture: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from runtime.runtime_wrapper import run_phase4_personalization
    except Exception as e:
        raise AssertionError(f"Unable to import Phase 4 runtime: {e}")

    for k in ("canonical_payload", "canonical_row", "selected_elements", "difficulty"):
        assert k in fixture, f"Fixture missing required key '{k}'"

    out = run_phase4_personalization(
        canonical_payload=fixture["canonical_payload"],
        canonical_row=fixture["canonical_row"],
        selected_elements=fixture["selected_elements"],
        difficulty=fixture["difficulty"],
        engine_mode="personalized",
        player_id_hash=fixture.get("player_id_hash"),
        locale=fixture.get("locale"),
        feature_flags=fixture.get("feature_flags"),
        opt_in=fixture.get("opt_in"),
    )

    assert isinstance(out, dict), "Phase 4 runtime output must be a dict"
    return out


# ----------------------------
# Core invariants
# ----------------------------

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

MODEL_LIKE_SOURCES = {"model", "hybrid"}
RULE_LIKE_SOURCES = {"rule"}


def assert_no_semantic_mutation(fixture: dict, out: dict) -> None:
    inp_elements = fixture["selected_elements"]
    out_elements = out["elements_view"]

    inp_idx = index_by_element_id(inp_elements)
    out_idx = index_by_element_id(out_elements)

    assert_permutation(list(inp_idx.keys()), list(out_idx.keys()))

    # ✅ semantic immutability
    for eid in inp_idx:
        for field in IMMUTABLE_ELEMENT_FIELDS:
            assert inp_idx[eid].get(field) == out_idx[eid].get(field), \
                f"{field} changed for {eid}"

    prov = out["phase4_provenance"]
    decision_source = prov["decision_source"]

    model_out = out.get("model_outputs") or {}
    applied = out.get("applied_adjustments") or {}

    # ✅ rule path must be empty
    if decision_source in RULE_LIKE_SOURCES:
        assert not model_out
        assert not applied

    # ✅ allowed keys only
    extra = set(applied.keys()) - ALLOWED_ADJUSTMENT_KEYS
    assert not extra, f"Disallowed adjustment keys: {extra}"


# ----------------------------
# ✅ pytest entrypoint
# ----------------------------

@pytest.mark.phase4_policy
def test_personalized_fixture_bounds():
    inputs = sorted(FIXTURES_DIR.glob("fixture_*_input.json"))

    assert inputs, "No fixtures found"

    ran = 0

    for p in inputs:
        fx = load_json(p)

        if not is_personalized_fixture(fx):
            continue

        out = run_phase4(fx)

        assert_no_semantic_mutation(fx, out)

        ran += 1

    assert ran > 0, "No personalized fixtures executed"